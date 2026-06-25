"""
Service d'écoute MQTT : reçoit les scans de carte simulés (envoyés par P2) sur
le topic `campus/reader/scan` et leur applique la même logique que l'endpoint
HTTP /api/iot/scan/ (vérification signature + nonce + horodatage).

Lancement (en parallèle du serveur web) :
    python manage.py mqtt_listener

Le message MQTT attendu est un JSON identique à celui de l'endpoint HTTP :
    {"uid": "...", "terminal_id": "...", "timestamp": 1718450000000,
     "nonce": "<hex>", "signature": "<base64>", "type": "identification"}
"""
import json
import logging

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from rest_framework.exceptions import APIException

from iot.models import TypeScan
from iot.services import verifier_scan

logger = logging.getLogger("smartcampus.securite")


class Command(BaseCommand):
    help = "Écoute le broker MQTT et traite les scans de carte entrants."

    def handle(self, *args, **options):
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="smartcampus-backend-listener",
        )

        if settings.MQTT_USERNAME:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        self.stdout.write(
            self.style.NOTICE(
                f"Connexion au broker MQTT {settings.MQTT_HOST}:{settings.MQTT_PORT} "
                f"(topic « {settings.MQTT_TOPIC_SCAN} »)…"
            )
        )
        # `connect` peut lever si le broker est indisponible : on laisse la
        # boucle de reconnexion automatique gérer les coupures réseau.
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Arrêt demandé (Ctrl-C)."))
            client.disconnect()

    # ----- Callbacks MQTT -----
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            client.subscribe(settings.MQTT_TOPIC_SCAN, qos=1)
            self.stdout.write(self.style.SUCCESS("Connecté et abonné."))
        else:
            self.stderr.write(f"Échec de connexion MQTT (code {reason_code}).")

    def _on_disconnect(self, client, userdata, *args):
        # Signature variable selon la version de paho ; on logge simplement.
        logger.warning("Déconnecté du broker MQTT — tentative de reconnexion.")

    def _on_message(self, client, userdata, message):
        """Traite un message : parse JSON puis applique verifier_scan."""
        # Les connexions DB peuvent expirer entre deux messages : on nettoie.
        close_old_connections()

        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.warning("Message MQTT illisible (JSON invalide) ignoré.")
            return

        type_scan = payload.pop("type", TypeScan.IDENTIFICATION)
        try:
            resultat = verifier_scan(
                payload, type_scan=type_scan, consommer=True
            )
            logger.info(
                "Scan MQTT accepté uid=%s terminal=%s",
                resultat.etudiant.uid_carte,
                resultat.terminal.code,
            )
        except APIException as erreur:
            # Refus métier (carte/terminal/signature/horodatage/rejeu) : déjà
            # journalisé par verifier_scan, on trace le code applicatif.
            logger.info("Scan MQTT refusé : %s", getattr(erreur, "default_code", erreur))
        except Exception:  # robustesse : un message ne doit jamais tuer la boucle
            logger.exception("Erreur inattendue lors du traitement d'un scan MQTT.")
        finally:
            close_old_connections()
