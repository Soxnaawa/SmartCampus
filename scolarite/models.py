"""Modèle des paiements de scolarité (le statut, lui, est calculé, pas stocké)."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import ModeleBase
from etudiants.models import Etudiant


class TypePeriode(models.TextChoices):
    MENSUEL = "mensuel", "Mensuel"
    SEMESTRIEL = "semestriel", "Semestriel"
    EXONERATION = "exoneration", "Exonération"


class StatutPaiement(models.TextChoices):
    VALIDE = "valide", "Valide"
    ANNULE = "annule", "Annulé"
    REMBOURSE = "rembourse", "Remboursé"


class PaiementScolarite(ModeleBase):
    """Un encaissement de scolarité (ou une exonération) pour une période."""

    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.PROTECT,
        related_name="paiements",
        verbose_name="Étudiant",
    )
    type_periode = models.CharField(
        max_length=12,
        choices=TypePeriode.choices,
        verbose_name="Type de période",
    )
    periode_couverte = models.CharField(
        max_length=7,
        verbose_name="Période couverte",
        help_text="Ex : 2025-11 (mois) ou 2025-S1 (semestre).",
    )
    montant = models.BigIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Montant (centimes FCFA)",
        help_text="> 0, sauf exonération où 0 est autorisé.",
    )
    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="encaissements",
        verbose_name="Caissier",
        null=True,
        blank=True,
    )
    statut = models.CharField(
        max_length=10,
        choices=StatutPaiement.choices,
        default=StatutPaiement.VALIDE,
        verbose_name="Statut",
    )

    class Meta:
        verbose_name = "Paiement de scolarité"
        verbose_name_plural = "Paiements de scolarité"
        ordering = ["-cree_le"]
        indexes = [
            models.Index(fields=["etudiant"]),
            models.Index(fields=["periode_couverte"]),
        ]

    def __str__(self):
        return f"{self.etudiant.uid_carte} — {self.periode_couverte} ({self.type_periode})"

    @property
    def numero_recu(self) -> str:
        """Numéro de reçu lisible dérivé de l'UUID (les 8 premiers hex)."""
        return f"REC-{str(self.id).split('-')[0].upper()}"
