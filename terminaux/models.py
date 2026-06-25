"""Modèle Terminal : point d'interaction physique avec la carte."""
from django.db import models

from core.models import ModeleBase


class TypeTerminal(models.TextChoices):
    """Catégorie fonctionnelle d'un terminal."""

    RESTAURANT = "restaurant", "Restaurant"
    REPROGRAPHIE = "reprographie", "Reprographie"
    TRANSPORT = "transport", "Transport"
    RECHARGE = "recharge", "Recharge"
    CONTROLE = "controle", "Contrôle"


class Terminal(ModeleBase):
    """Terminal identifié par un code lisible (ex : RESTO-01)."""

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Code",
        help_text="Code unique du terminal, ex : RESTO-01.",
    )
    type = models.CharField(
        max_length=20,
        choices=TypeTerminal.choices,
        verbose_name="Type",
    )
    libelle = models.CharField(max_length=100, blank=True, verbose_name="Libellé")
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Terminal"
        verbose_name_plural = "Terminaux"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} [{self.get_type_display()}]"
