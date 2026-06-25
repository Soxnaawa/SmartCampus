"""Modèles monétiques : solde (porte-monnaie) et transactions.

Rappel important (§2) : tous les montants sont des ENTIERS en centimes de FCFA.
Jamais de float. 750 FCFA → 75000.
"""
from django.core.validators import MinValueValidator
from django.db import models

from core.models import ModeleBase
from etudiants.models import Etudiant
from terminaux.models import Terminal


class Solde(ModeleBase):
    """Porte-monnaie électronique d'un étudiant (un seul par étudiant)."""

    etudiant = models.OneToOneField(
        Etudiant,
        on_delete=models.CASCADE,
        related_name="solde",
        verbose_name="Étudiant",
    )
    montant = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant (centimes FCFA)",
    )
    mis_a_jour = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")
    # Verrou optimiste : incrémenté à chaque écriture pour détecter les
    # modifications concurrentes (anti double-débit) en complément du verrou
    # pessimiste select_for_update utilisé lors du débit.
    version = models.PositiveIntegerField(default=0, verbose_name="Version")

    class Meta:
        verbose_name = "Solde"
        verbose_name_plural = "Soldes"

    def __str__(self):
        return f"Solde {self.etudiant.uid_carte} : {self.montant} centimes"

    @property
    def montant_fcfa(self) -> int:
        """Montant en FCFA (pour affichage)."""
        return self.montant // 100


class TypeTransaction(models.TextChoices):
    DEBIT = "debit", "Débit"
    CREDIT = "credit", "Crédit"
    REMBOURSEMENT = "remboursement", "Remboursement"


class StatutTransaction(models.TextChoices):
    VALIDE = "valide", "Validée"
    REFUSE = "refuse", "Refusée"
    SUSPECT = "suspect", "Suspecte"
    ANNULE = "annule", "Annulée"


class Transaction(ModeleBase):
    """Mouvement financier sur le porte-monnaie d'un étudiant."""

    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Étudiant",
    )
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
        verbose_name="Terminal",
    )
    type = models.CharField(max_length=15, choices=TypeTransaction.choices)
    montant = models.BigIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Montant (centimes FCFA)",
    )
    statut = models.CharField(
        max_length=10,
        choices=StatutTransaction.choices,
        default=StatutTransaction.VALIDE,
    )
    # Score de fraude (0–100), rempli ultérieurement par le service IA (P4).
    score_fraude = models.PositiveSmallIntegerField(null=True, blank=True)
    # Nonce anti-rejeu : un nonce ne peut servir qu'une seule fois.
    nonce = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Nonce (anti-rejeu)",
    )
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-cree_le"]
        indexes = [
            models.Index(fields=["etudiant"]),
            models.Index(fields=["terminal"]),
            models.Index(fields=["cree_le"]),
            models.Index(fields=["statut"]),
        ]

    def __str__(self):
        return f"{self.type} {self.montant} ({self.statut}) — {self.etudiant.uid_carte}"
