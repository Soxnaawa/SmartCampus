"""Tests du calcul de statut de scolarité (tous les cas — §6.c)."""
from datetime import date

import pytest

from etudiants.models import Etudiant, StatutCarte
from scolarite.models import PaiementScolarite, StatutPaiement, TypePeriode
from scolarite.services import calculer_statut, statut_pour_controle

pytestmark = pytest.mark.django_db


def _etudiant(uid="SC-2025-09999"):
    e = Etudiant(
        uid_carte=uid,
        email=f"{uid}@test.sn",
        filiere="DIC2 — M1",
        statut=StatutCarte.ACTIF,
        certificat_pub="(non utilisé ici)",
    )
    e.nom, e.prenom, e.matricule = "Test", "Etu", "MAT"
    e.save()
    return e


def _payer(etu, type_periode, periode, montant=5_000_000):
    return PaiementScolarite.objects.create(
        etudiant=etu,
        type_periode=type_periode,
        periode_couverte=periode,
        montant=montant,
        statut=StatutPaiement.VALIDE,
    )


# ---------------------------------------------------------------------------
# Mensuel
# ---------------------------------------------------------------------------
def test_mensuel_a_jour():
    etu = _etudiant()
    # Le 20/11 (après le délai de grâce du 15) : le mois exigible est 2025-11.
    _payer(etu, TypePeriode.MENSUEL, "2025-11")
    res = calculer_statut(etu, aujourdhui=date(2025, 11, 20))
    assert res["statut"] == "a_jour"
    assert res["mois_de_retard"] == 0
    assert res["token_valide"] is True
    assert res["derniere_periode"] == "2025-11"


def test_mensuel_en_retard_compte_les_mois():
    etu = _etudiant()
    # Dernier mois payé = septembre ; exigible = novembre ⇒ 2 mois de retard.
    _payer(etu, TypePeriode.MENSUEL, "2025-09")
    res = calculer_statut(etu, aujourdhui=date(2025, 11, 20))
    assert res["statut"] == "en_retard"
    assert res["mois_de_retard"] == 2
    assert res["token_valide"] is False


def test_mensuel_delai_de_grace_avant_le_15():
    etu = _etudiant()
    # Le 10/11 (dans la grâce) : le mois exigible est encore octobre.
    _payer(etu, TypePeriode.MENSUEL, "2025-10")
    res = calculer_statut(etu, aujourdhui=date(2025, 11, 10))
    assert res["statut"] == "a_jour"
    assert res["mois_de_retard"] == 0


def test_mensuel_sans_aucun_paiement_est_en_retard():
    etu = _etudiant()
    res = calculer_statut(etu, aujourdhui=date(2025, 11, 20))
    assert res["statut"] == "en_retard"
    assert res["mois_de_retard"] >= 1
    assert res["derniere_periode"] is None


# ---------------------------------------------------------------------------
# Semestriel
# ---------------------------------------------------------------------------
def test_semestriel_a_jour():
    etu = _etudiant()
    _payer(etu, TypePeriode.SEMESTRIEL, "2025-S1", montant=45_000_000)
    res = calculer_statut(etu, aujourdhui=date(2025, 11, 20))
    assert res["regime"] == "semestriel"
    assert res["statut"] == "a_jour"
    assert res["mois_de_retard"] == 0


def test_semestriel_en_retard():
    etu = _etudiant()
    # Paie S1 2025 alors qu'on est en avril 2026 (S2 2026 exigible).
    _payer(etu, TypePeriode.SEMESTRIEL, "2025-S1", montant=45_000_000)
    res = calculer_statut(etu, aujourdhui=date(2026, 4, 1))
    assert res["statut"] == "en_retard"
    # 3 semestres d'écart (S2-2025, S1-2026, S2-2026) × 6 mois.
    assert res["mois_de_retard"] == 18


# ---------------------------------------------------------------------------
# Exonération
# ---------------------------------------------------------------------------
def test_exoneration_prioritaire():
    etu = _etudiant()
    _payer(etu, TypePeriode.EXONERATION, "2025-S1", montant=0)
    res = calculer_statut(etu, aujourdhui=date(2026, 6, 1))
    assert res["statut"] == "exonere"
    assert res["token_valide"] is True
    assert res["mois_de_retard"] == 0


# ---------------------------------------------------------------------------
# Contrat figé de la vue de contrôle
# ---------------------------------------------------------------------------
def test_format_controle_ne_fuit_pas_d_infos_sensibles():
    etu = _etudiant()
    _payer(etu, TypePeriode.MENSUEL, "2025-11")
    sortie = statut_pour_controle(etu, aujourdhui=date(2025, 11, 20))
    # Champs exactement conformes au contrat.
    assert set(sortie.keys()) == {
        "uid",
        "filiere",
        "statut",
        "derniere_periode",
        "mois_de_retard",
        "token_valide",
    }
    # Aucune donnée personnelle/financière exposée.
    valeurs = str(sortie)
    assert "Test" not in valeurs and "MAT" not in valeurs
