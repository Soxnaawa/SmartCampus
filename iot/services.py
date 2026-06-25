"""
Service de vérification des scans de carte (logique partagée MQTT / HTTP /
débit). C'est ici que vit la sécurité « carte ↔ terminal » décrite au §6.a.

Étapes (dans l'ordre) :
    1. l'UID existe et la carte est `actif` ;
    2. le terminal existe et est `actif` ;
    3. l'horodatage est récent (TTL paramétrable, défaut 30 s) ;
    4. la signature RSA du nonce est valide (clé publique du certificat X.509) ;
    5. le nonce n'a jamais été utilisé (anti-rejeu) → consommation atomique.

Si une étape échoue, on lève une exception métier (voir iot.exceptions) et on
journalise le refus dans le logger de sécurité. Aucune ligne n'est consommée en
cas d'échec : un nonce n'est « brûlé » que pour un scan entièrement valide.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction

from core.signatures import verifier_signature_nonce
from etudiants.models import Etudiant
from terminaux.models import Terminal

from . import exceptions as exc
from .models import JournalScan, TypeScan

logger = logging.getLogger("smartcampus.securite")

CHAMPS_REQUIS = ("uid", "terminal_id", "timestamp", "nonce", "signature")


@dataclass
class ResultatScan:
    """Résultat d'une vérification de scan réussie."""

    etudiant: Etudiant
    terminal: Terminal
    journal: JournalScan | None  # None si consommer=False


def _refus(motif: str, **contexte):
    """Journalise un refus de scan dans le logger de sécurité."""
    logger.warning("Scan refusé (%s) %s", motif, contexte)


def verifier_scan(
    payload: dict,
    *,
    type_scan: str = TypeScan.IDENTIFICATION,
    consommer: bool = True,
) -> ResultatScan:
    """Vérifie un message de scan et, si tout est valide, consomme le nonce.

    `payload` doit contenir : uid, terminal_id, timestamp (epoch ms), nonce
    (hex), signature (base64). Lève une `APIException` métier sinon.
    """
    # --- 0. Présence des champs ------------------------------------------
    manquants = [c for c in CHAMPS_REQUIS if c not in payload or payload[c] in (None, "")]
    if manquants:
        _refus("champs_manquants", manquants=manquants)
        raise exc.DonneesScanInvalides(
            f"Champs manquants : {', '.join(manquants)}."
        )

    uid = str(payload["uid"])
    code_terminal = str(payload["terminal_id"])
    nonce = str(payload["nonce"])
    signature = str(payload["signature"])

    try:
        horodatage_ms = int(payload["timestamp"])
    except (TypeError, ValueError):
        _refus("timestamp_non_entier", uid=uid)
        raise exc.HorodatageInvalide("Le timestamp doit être un entier (ms).")

    # --- 1. Carte ---------------------------------------------------------
    etudiant = Etudiant.objects.filter(uid_carte=uid).first()
    if etudiant is None:
        _refus("carte_introuvable", uid=uid)
        raise exc.CarteIntrouvable()
    if not etudiant.carte_active:
        _refus("carte_inactive", uid=uid, statut=etudiant.statut)
        raise exc.CarteInactive()

    # --- 2. Terminal ------------------------------------------------------
    terminal = Terminal.objects.filter(code=code_terminal).first()
    if terminal is None:
        _refus("terminal_introuvable", terminal=code_terminal)
        raise exc.TerminalIntrouvable()
    if not terminal.actif:
        _refus("terminal_inactif", terminal=code_terminal)
        raise exc.TerminalInactif()

    # --- 3. Fraîcheur de l'horodatage (anti-rejeu temporel) --------------
    maintenant_ms = int(time.time() * 1000)
    ttl_ms = settings.SCAN_TTL_SECONDES * 1000
    age_ms = maintenant_ms - horodatage_ms
    # On rejette si trop ancien OU trop dans le futur (dérive d'horloge > 5 s).
    if age_ms > ttl_ms or age_ms < -5000:
        _refus("horodatage_expire", uid=uid, age_ms=age_ms, ttl_ms=ttl_ms)
        raise exc.HorodatageInvalide()

    # --- 4. Signature de la carte ----------------------------------------
    if not verifier_signature_nonce(etudiant.certificat_pub, nonce, signature):
        _refus("signature_invalide", uid=uid)
        raise exc.SignatureInvalide()

    # --- 5. Anti-rejeu : consommation atomique du nonce ------------------
    journal = None
    if consommer:
        journal = _consommer_nonce(
            uid=uid,
            nonce=nonce,
            etudiant=etudiant,
            terminal=terminal,
            type_scan=type_scan,
            horodatage_ms=horodatage_ms,
        )

    logger.info(
        "Scan accepté uid=%s terminal=%s type=%s", uid, code_terminal, type_scan
    )
    return ResultatScan(etudiant=etudiant, terminal=terminal, journal=journal)


def _consommer_nonce(*, uid, nonce, etudiant, terminal, type_scan, horodatage_ms):
    """Insère le nonce dans le journal ; échoue si déjà présent (rejeu)."""
    try:
        with transaction.atomic():
            return JournalScan.objects.create(
                uid=uid,
                etudiant=etudiant,
                terminal=terminal,
                type_scan=type_scan,
                nonce=nonce,
                horodatage_carte=horodatage_ms,
            )
    except IntegrityError:
        _refus("rejeu_nonce", uid=uid, nonce=nonce[:12] + "…")
        raise exc.RejeuDetecte()


def nonce_deja_consomme(nonce: str) -> bool:
    """Indique si un nonce a déjà été consommé (utile pour les tests)."""
    return JournalScan.objects.filter(nonce=nonce).exists()
