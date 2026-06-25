"""Tests de sécurité de la vérification de scan (signature, TTL, carte, rejeu)."""
import secrets
import time

import pytest

from core.signatures import generer_paire_et_certificat
from etudiants.models import StatutCarte
from iot import exceptions as exc
from iot.models import JournalScan, TypeScan
from iot.services import verifier_scan

pytestmark = pytest.mark.django_db


def test_scan_valide_consomme_le_nonce(etudiant, terminal, paire_cles, construire_scan):
    payload = construire_scan(etudiant.uid_carte, terminal.code, paire_cles["priv"])
    res = verifier_scan(payload, type_scan=TypeScan.IDENTIFICATION)
    assert res.etudiant == etudiant
    assert JournalScan.objects.filter(nonce=payload["nonce"]).exists()


def test_signature_invalide_rejetee(etudiant, terminal, construire_scan):
    # On signe avec une AUTRE clé que celle du certificat stocké.
    autre_priv, _ = generer_paire_et_certificat("SC-ATTAQUANT")
    payload = construire_scan(etudiant.uid_carte, terminal.code, autre_priv)
    with pytest.raises(exc.SignatureInvalide):
        verifier_scan(payload)
    # Aucun nonce consommé en cas d'échec.
    assert not JournalScan.objects.filter(nonce=payload["nonce"]).exists()


def test_horodatage_expire_rejete(etudiant, terminal, paire_cles, construire_scan):
    vieux = int(time.time() * 1000) - 60_000  # 60 s dans le passé (TTL = 30 s)
    payload = construire_scan(
        etudiant.uid_carte, terminal.code, paire_cles["priv"], timestamp=vieux
    )
    with pytest.raises(exc.HorodatageInvalide):
        verifier_scan(payload)


def test_rejeu_nonce_rejete(etudiant, terminal, paire_cles, construire_scan):
    payload = construire_scan(etudiant.uid_carte, terminal.code, paire_cles["priv"])
    verifier_scan(payload)
    with pytest.raises(exc.RejeuDetecte):
        verifier_scan(payload)


def test_carte_bloquee_rejetee(etudiant, terminal, paire_cles, construire_scan):
    etudiant.statut = StatutCarte.BLOQUE
    etudiant.save(update_fields=["statut"])
    payload = construire_scan(etudiant.uid_carte, terminal.code, paire_cles["priv"])
    with pytest.raises(exc.CarteInactive):
        verifier_scan(payload)


def test_carte_inconnue_rejetee(terminal, paire_cles, construire_scan):
    payload = construire_scan("SC-INCONNU", terminal.code, paire_cles["priv"])
    with pytest.raises(exc.CarteIntrouvable):
        verifier_scan(payload)


def test_terminal_inconnu_rejete(etudiant, paire_cles, construire_scan):
    payload = construire_scan(etudiant.uid_carte, "TERM-XXX", paire_cles["priv"])
    with pytest.raises(exc.TerminalIntrouvable):
        verifier_scan(payload)


def test_champs_manquants_rejetes(etudiant):
    with pytest.raises(exc.DonneesScanInvalides):
        verifier_scan({"uid": etudiant.uid_carte})
