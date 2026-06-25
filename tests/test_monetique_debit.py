"""Tests du débit atomique et de l'anti-rejeu (§6.a et §6.b)."""
import pytest

from iot import exceptions as exc
from monetique.models import Solde, StatutTransaction, TypeTransaction
from monetique.services import debiter

pytestmark = pytest.mark.django_db


def test_debit_valide_decremente_le_solde(etudiant, terminal, paire_cles, construire_scan):
    payload = construire_scan(
        etudiant.uid_carte, terminal.code, paire_cles["priv"], montant=30_000
    )
    tx = debiter(payload, montant=30_000)

    assert tx.statut == StatutTransaction.VALIDE
    assert tx.type == TypeTransaction.DEBIT
    solde = Solde.objects.get(etudiant=etudiant)
    assert solde.montant == 70_000  # 100 000 - 30 000
    assert solde.version == 1


def test_debit_solde_insuffisant_est_refuse_sans_modifier_le_solde(
    etudiant, terminal, paire_cles, construire_scan
):
    payload = construire_scan(
        etudiant.uid_carte, terminal.code, paire_cles["priv"], montant=999_999
    )
    tx = debiter(payload, montant=999_999)

    assert tx.statut == StatutTransaction.REFUSE
    solde = Solde.objects.get(etudiant=etudiant)
    assert solde.montant == 100_000  # inchangé


def test_rejeu_du_meme_nonce_est_rejete(
    etudiant, terminal, paire_cles, construire_scan
):
    payload = construire_scan(
        etudiant.uid_carte, terminal.code, paire_cles["priv"], montant=10_000
    )
    # 1er débit OK.
    debiter(payload, montant=10_000)
    # 2e débit avec le MÊME nonce ⇒ rejeu détecté, aucun double-débit.
    with pytest.raises(exc.RejeuDetecte):
        debiter(payload, montant=10_000)

    solde = Solde.objects.get(etudiant=etudiant)
    assert solde.montant == 90_000  # un seul débit appliqué


def test_deux_debits_nonces_differents_se_cumulent(
    etudiant, terminal, paire_cles, construire_scan
):
    p1 = construire_scan(etudiant.uid_carte, terminal.code, paire_cles["priv"], montant=10_000)
    p2 = construire_scan(etudiant.uid_carte, terminal.code, paire_cles["priv"], montant=20_000)
    debiter(p1, montant=10_000)
    debiter(p2, montant=20_000)
    solde = Solde.objects.get(etudiant=etudiant)
    assert solde.montant == 70_000
    assert solde.version == 2
