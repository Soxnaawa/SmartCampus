"""
Logique métier monétique : débit atomique, crédit, blocage, statistiques.

Décision (signalée) : un débit refusé pour solde insuffisant n'est PAS une
exception ; le service crée et renvoie une transaction au statut `refuse`, et la
vue choisit le code HTTP (402). À l'inverse, les échecs de vérification de scan
(carte/terminal/signature/horodatage/rejeu) lèvent des exceptions métier et ne
créent aucune transaction.
"""
from __future__ import annotations

import logging
import secrets

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from etudiants.models import Etudiant, StatutCarte
from iot.models import TypeScan
from iot.services import verifier_scan

from .models import (
    Solde,
    StatutTransaction,
    Transaction,
    TypeTransaction,
)

logger = logging.getLogger("smartcampus.securite")


def _solde_verrouille(etudiant: Etudiant) -> Solde:
    """Récupère (ou crée) le solde de l'étudiant en le verrouillant en écriture.

    À appeler **uniquement** dans un bloc `transaction.atomic()`. Le
    `select_for_update()` garantit qu'aucune autre transaction ne peut lire/écrire
    ce solde tant que la transaction courante n'est pas terminée (anti
    double-débit pessimiste).
    """
    solde, _ = Solde.objects.get_or_create(etudiant=etudiant)
    # On reverrouille la ligne maintenant qu'elle existe à coup sûr.
    return Solde.objects.select_for_update().get(pk=solde.pk)


def debiter(payload: dict, *, montant: int) -> Transaction:
    """Débite le solde d'une carte après vérification complète du scan signé.

    `payload` = enveloppe signée (uid, terminal_id, timestamp, nonce, signature).
    `montant` = centimes FCFA (> 0).

    Renvoie la `Transaction` créée (statut `valide` ou `refuse`). Lève une
    exception métier si la vérification du scan échoue (aucune transaction créée).
    """
    if montant <= 0:
        from iot.exceptions import DonneesScanInvalides

        raise DonneesScanInvalides("Le montant doit être strictement positif.")

    # 1) Vérification + consommation du nonce (anti-rejeu). Lève si invalide.
    resultat = verifier_scan(payload, type_scan=TypeScan.DEBIT, consommer=True)
    etudiant, terminal = resultat.etudiant, resultat.terminal
    nonce = str(payload["nonce"])

    # 2) Débit atomique sous verrou pessimiste.
    with transaction.atomic():
        solde = _solde_verrouille(etudiant)

        if montant > solde.montant:
            # Solde insuffisant : on trace une transaction refusée (auditable),
            # sans modifier le solde.
            tx = Transaction.objects.create(
                etudiant=etudiant,
                terminal=terminal,
                type=TypeTransaction.DEBIT,
                montant=montant,
                statut=StatutTransaction.REFUSE,
                nonce=nonce,
                metadata={"motif": "solde_insuffisant", "solde": solde.montant},
            )
            logger.info(
                "Débit refusé (solde insuffisant) uid=%s demande=%s solde=%s",
                etudiant.uid_carte,
                montant,
                solde.montant,
            )
            return tx

        # Débit accepté : on décrémente, on incrémente la version (verrou
        # optimiste) et on horodate.
        solde.montant -= montant
        solde.version += 1
        solde.save(update_fields=["montant", "version", "mis_a_jour"])

        tx = Transaction.objects.create(
            etudiant=etudiant,
            terminal=terminal,
            type=TypeTransaction.DEBIT,
            montant=montant,
            statut=StatutTransaction.VALIDE,
            nonce=nonce,
            metadata={"solde_apres": solde.montant},
        )
    logger.info(
        "Débit validé uid=%s montant=%s solde_apres=%s",
        etudiant.uid_carte,
        montant,
        solde.montant,
    )
    return tx


def crediter(
    *,
    etudiant: Etudiant,
    montant: int,
    terminal=None,
    type_transaction: str = TypeTransaction.CREDIT,
    nonce: str | None = None,
    metadata: dict | None = None,
) -> Transaction:
    """Recharge (crédite) le solde d'un étudiant de façon atomique.

    La recharge se fait au guichet (caissier/admin authentifié JWT) : pas de
    signature de carte requise. Le nonce est généré côté serveur s'il n'est pas
    fourni, afin de conserver l'unicité de la colonne `nonce`.
    """
    if montant <= 0:
        from iot.exceptions import DonneesScanInvalides

        raise DonneesScanInvalides("Le montant doit être strictement positif.")

    nonce = nonce or secrets.token_hex(16)

    with transaction.atomic():
        solde = _solde_verrouille(etudiant)
        solde.montant += montant
        solde.version += 1
        solde.save(update_fields=["montant", "version", "mis_a_jour"])

        tx = Transaction.objects.create(
            etudiant=etudiant,
            terminal=terminal,
            type=type_transaction,
            montant=montant,
            statut=StatutTransaction.VALIDE,
            nonce=nonce,
            metadata=metadata or {"solde_apres": solde.montant},
        )
    logger.info(
        "Crédit (%s) uid=%s montant=%s solde_apres=%s",
        type_transaction,
        etudiant.uid_carte,
        montant,
        solde.montant,
    )
    return tx


def bloquer_carte(etudiant: Etudiant) -> Etudiant:
    """Passe la carte d'un étudiant au statut `bloque`."""
    etudiant.statut = StatutCarte.BLOQUE
    etudiant.save(update_fields=["statut"])
    logger.warning("Carte bloquée uid=%s", etudiant.uid_carte)
    return etudiant


def statistiques_dashboard() -> dict:
    """Agrège les KPIs globaux pour le tableau de bord administrateur."""
    debut_jour = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    transactions = Transaction.objects.all()
    valides = transactions.filter(statut=StatutTransaction.VALIDE)

    volume_debit = (
        valides.filter(type=TypeTransaction.DEBIT).aggregate(s=Sum("montant"))["s"]
        or 0
    )
    volume_credit = (
        valides.filter(type=TypeTransaction.CREDIT).aggregate(s=Sum("montant"))["s"]
        or 0
    )
    solde_total = Solde.objects.aggregate(s=Sum("montant"))["s"] or 0

    repartition = {
        ligne["statut"]: ligne["n"]
        for ligne in transactions.values("statut").annotate(n=Count("id"))
    }

    return {
        "etudiants_total": Etudiant.objects.count(),
        "cartes_actives": Etudiant.objects.filter(
            statut=StatutCarte.ACTIF
        ).count(),
        "cartes_bloquees": Etudiant.objects.filter(
            statut=StatutCarte.BLOQUE
        ).count(),
        "transactions_total": transactions.count(),
        "transactions_aujourdhui": transactions.filter(
            cree_le__gte=debut_jour
        ).count(),
        "repartition_statut": repartition,
        "volume_debit_centimes": volume_debit,
        "volume_credit_centimes": volume_credit,
        "solde_total_centimes": solde_total,
    }
