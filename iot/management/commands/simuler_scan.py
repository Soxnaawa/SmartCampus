"""
Simule un scan de carte signé (utile pour tester sans hardware).

Construit un message valide (nonce aléatoire + signature RSA via la clé privée
de test générée par `seed_data` dans certs/cards/<uid>.pem), puis :
- l'affiche en JSON (à copier dans un curl vers /api/iot/scan/), et
- éventuellement le publie sur le broker MQTT (`--mqtt`).

Exemples :
    python manage.py simuler_scan --uid SC-2025-00001 --terminal RESTO-01
    python manage.py simuler_scan --uid SC-2025-00001 --terminal RESTO-01 --mqtt
"""
import json
import secrets
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.signatures import signer_nonce


class Command(BaseCommand):
    help = "Génère (et publie) un message de scan signé pour une carte de test."

    def add_arguments(self, parser):
        parser.add_argument("--uid", required=True, help="UID de la carte.")
        parser.add_argument("--terminal", required=True, help="Code du terminal.")
        parser.add_argument(
            "--type", default="identification", help="Type de scan."
        )
        parser.add_argument(
            "--mqtt",
            action="store_true",
            help="Publie le message sur le broker MQTT configuré.",
        )

    def handle(self, *args, **options):
        uid = options["uid"]
        chemin_cle = Path(settings.BASE_DIR) / "certs" / "cards" / f"{uid}.pem"
        if not chemin_cle.exists():
            raise CommandError(
                f"Clé privée introuvable pour {uid} ({chemin_cle}). "
                "Lancez d'abord `python manage.py seed_data`."
            )

        cle_privee_pem = chemin_cle.read_text()
        nonce = secrets.token_hex(32)
        signature = signer_nonce(cle_privee_pem, nonce)

        message = {
            "uid": uid,
            "terminal_id": options["terminal"],
            "timestamp": int(time.time() * 1000),
            "nonce": nonce,
            "signature": signature,
            "type": options["type"],
        }

        self.stdout.write(json.dumps(message, indent=2))

        if options["mqtt"]:
            self._publier(message)

    def _publier(self, message):
        import paho.mqtt.client as mqtt

        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        if settings.MQTT_USERNAME:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=30)
        client.loop_start()
        client.publish(settings.MQTT_TOPIC_SCAN, json.dumps(message), qos=1)
        time.sleep(0.5)  # laisse le temps à la publication de partir
        client.loop_stop()
        client.disconnect()
        self.stdout.write(
            self.style.SUCCESS(
                f"Message publié sur « {settings.MQTT_TOPIC_SCAN} »."
            )
        )
