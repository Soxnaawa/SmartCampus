"""
Calcul DYNAMIQUE du statut de scolarité (cahier des charges §6.c).

Le statut n'est jamais stocké : il est recalculé à partir des paiements valides
et de la date courante. Trois régimes :

- exoneration : un paiement valide de type `exoneration` ⇒ statut `exonere` ;
- mensuel     : à jour si le mois exigible est payé (délai de grâce de 5 jours
                après le 10, soit jusqu'au 15) ;
- semestriel  : à jour si le semestre exigible est payé (S1≈octobre, S2≈mars ;
                délai de grâce de 15 jours après le début du semestre).

Décisions signalées (cas non détaillés par le cahier) :
- Régime déterminé d'après les paiements de l'étudiant : si des paiements
  semestriels existent (et aucun mensuel) ⇒ régime semestriel, sinon mensuel.
- `mois_de_retard` en semestriel = nombre de semestres impayés × 6.
- Sans aucun paiement mensuel, le retard est compté depuis le début de l'année
  académique (octobre).

Le format de sortie de `statut_pour_controle` est le CONTRAT FIGÉ attendu par
l'équipe — ne pas le modifier.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from etudiants.models import Etudiant

from .models import PaiementScolarite, StatutPaiement, TypePeriode

# Constantes métier
JOUR_LIMITE_MENSUEL = 15  # 10 + 5 jours de grâce
GRACE_SEMESTRE_JOURS = 15
MOIS_DEBUT_S1 = 10  # octobre
MOIS_DEBUT_S2 = 3   # mars


# ---------------------------------------------------------------------------
# Helpers mensuels
# ---------------------------------------------------------------------------
def _cle_mois(annee: int, mois: int) -> str:
    return f"{annee:04d}-{mois:02d}"


def _mois_precedent(annee: int, mois: int) -> tuple[int, int]:
    return (annee - 1, 12) if mois == 1 else (annee, mois - 1)


def _diff_mois(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Nombre de mois de a vers b (positif si b est après a)."""
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def _mois_exigible(aujourdhui: date) -> tuple[int, int]:
    """Mois dont le paiement est requis pour être à jour, grâce comprise.

    Avant le 15 (10 + 5 jours de grâce), le mois courant n'est pas encore
    exigible : on demande le mois précédent. Après, le mois courant est exigible.
    """
    if aujourdhui.day <= JOUR_LIMITE_MENSUEL:
        return _mois_precedent(aujourdhui.year, aujourdhui.month)
    return (aujourdhui.year, aujourdhui.month)


def _statut_mensuel(mois_payes: set[str], aujourdhui: date) -> dict:
    exigible = _mois_exigible(aujourdhui)
    cle_exigible = _cle_mois(*exigible)
    derniere = max(mois_payes) if mois_payes else None

    if cle_exigible in mois_payes:
        return {"statut": "a_jour", "mois_de_retard": 0, "derniere_periode": derniere}

    if mois_payes:
        # Retard = mois écoulés depuis le dernier mois payé jusqu'à l'exigible.
        annee_dp, mois_dp = (int(x) for x in derniere.split("-"))
        retard = _diff_mois((annee_dp, mois_dp), exigible)
    else:
        # Aucun paiement : on compte depuis le début de l'année académique.
        annee_acad = exigible[0] if exigible[1] >= MOIS_DEBUT_S1 else exigible[0] - 1
        debut = (annee_acad, MOIS_DEBUT_S1)
        retard = _diff_mois(debut, exigible) + 1

    retard = max(retard, 0)
    statut = "a_jour" if retard == 0 else "en_retard"
    return {"statut": statut, "mois_de_retard": retard, "derniere_periode": derniere}


# ---------------------------------------------------------------------------
# Helpers semestriels
# ---------------------------------------------------------------------------
def _semestre_courant(d: date) -> tuple[str, date]:
    """Renvoie (label, date_de_debut) du semestre contenant la date d."""
    if d.month >= MOIS_DEBUT_S1:               # oct, nov, déc → S1 (année d)
        return f"{d.year}-S1", date(d.year, MOIS_DEBUT_S1, 1)
    if d.month < MOIS_DEBUT_S2:                 # jan, fév → S1 (année d-1)
        return f"{d.year - 1}-S1", date(d.year - 1, MOIS_DEBUT_S1, 1)
    return f"{d.year}-S2", date(d.year, MOIS_DEBUT_S2, 1)  # mars..sept → S2


def _index_semestre(label: str) -> int:
    """Index ordonné d'un semestre (pour comparer/compter les retards)."""
    annee, sem = label.split("-")
    return int(annee) * 2 + (0 if sem == "S1" else 1)


def _semestre_precedent(label: str) -> str:
    annee, sem = label.split("-")
    annee = int(annee)
    return f"{annee}-S1" if sem == "S2" else f"{annee - 1}-S2"


def _statut_semestriel(sem_payes: set[str], aujourdhui: date) -> dict:
    label_courant, debut = _semestre_courant(aujourdhui)
    # Délai de grâce : pendant les 15 jours suivant le début, le semestre
    # courant n'est pas encore exigible (on demande le précédent).
    if aujourdhui <= debut + timedelta(days=GRACE_SEMESTRE_JOURS):
        exigible = _semestre_precedent(label_courant)
    else:
        exigible = label_courant

    derniere = max(sem_payes, key=_index_semestre) if sem_payes else None

    if exigible in sem_payes:
        return {"statut": "a_jour", "mois_de_retard": 0, "derniere_periode": derniere}

    if sem_payes:
        retard_sem = _index_semestre(exigible) - _index_semestre(derniere)
    else:
        retard_sem = 1
    retard_sem = max(retard_sem, 0)
    statut = "a_jour" if retard_sem == 0 else "en_retard"
    # Le contrat exige un nombre de MOIS : on convertit (1 semestre ≈ 6 mois).
    return {
        "statut": statut,
        "mois_de_retard": retard_sem * 6,
        "derniere_periode": derniere,
    }


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def calculer_statut(etudiant: Etudiant, aujourdhui: date | None = None) -> dict:
    """Calcule le statut de scolarité d'un étudiant.

    Renvoie un dict complet (statut, mois_de_retard, derniere_periode,
    regime, token_valide). La vue de contrôle n'en exposera qu'un sous-ensemble.
    """
    if aujourdhui is None:
        aujourdhui = timezone.localdate()

    paiements = etudiant.paiements.filter(statut=StatutPaiement.VALIDE)

    # 1) Exonération prioritaire.
    exonerations = paiements.filter(type_periode=TypePeriode.EXONERATION)
    if exonerations.exists():
        derniere = exonerations.order_by("-cree_le").first()
        return {
            "statut": "exonere",
            "mois_de_retard": 0,
            "derniere_periode": derniere.periode_couverte or None,
            "regime": "exoneration",
            "token_valide": True,
        }

    mensuels = set(
        paiements.filter(type_periode=TypePeriode.MENSUEL).values_list(
            "periode_couverte", flat=True
        )
    )
    semestriels = set(
        paiements.filter(type_periode=TypePeriode.SEMESTRIEL).values_list(
            "periode_couverte", flat=True
        )
    )

    # 2) Régime : semestriel seulement s'il y a des paiements semestriels et
    #    aucun mensuel ; sinon régime mensuel (cas par défaut, y compris vide).
    if semestriels and not mensuels:
        base = _statut_semestriel(semestriels, aujourdhui)
        regime = "semestriel"
    else:
        base = _statut_mensuel(mensuels, aujourdhui)
        regime = "mensuel"

    base["regime"] = regime
    base["token_valide"] = base["statut"] in ("a_jour", "exonere")
    return base


def statut_pour_controle(etudiant: Etudiant, aujourdhui: date | None = None) -> dict:
    """Format de sortie FIGÉ de /api/scolarite/statut/<uid>/ (contrat équipe).

    Ne renvoie QUE les champs publics du contrôle : aucun nom, aucune info
    financière (confidentialité en contexte de contrôle public, §6.c).
    """
    resultat = calculer_statut(etudiant, aujourdhui)
    return {
        "uid": etudiant.uid_carte,
        "filiere": etudiant.filiere,
        "statut": resultat["statut"],
        "derniere_periode": resultat["derniere_periode"],
        "mois_de_retard": resultat["mois_de_retard"],
        "token_valide": resultat["token_valide"],
    }
