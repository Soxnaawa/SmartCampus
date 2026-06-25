"""Journal des scans reçus (audit + anti-rejeu)."""
from django.db import models

from core.models import ModeleBase
from etudiants.models import Etudiant
from terminaux.models import Terminal


class TypeScan(models.TextChoices):
    """Intention d'un scan (selon le terminal qui l'émet)."""

    IDENTIFICATION = "identification", "Identification"
    DEBIT = "debit", "Débit"
    CREDIT = "credit", "Crédit"
    CONTROLE = "controle", "Contrôle"


class JournalScan(ModeleBase):
    """Trace d'un scan accepté.

    La colonne `nonce` est UNIQUE : elle constitue le point de vérité de la
    protection anti-rejeu. Insérer une ligne = « consommer » le nonce ; une
    seconde insertion du même nonce échoue (IntegrityError) → rejeu.
    """

    uid = models.CharField(max_length=20, verbose_name="UID scanné")
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scans",
    )
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scans",
    )
    type_scan = models.CharField(
        max_length=15,
        choices=TypeScan.choices,
        default=TypeScan.IDENTIFICATION,
    )
    nonce = models.CharField(max_length=64, unique=True, verbose_name="Nonce")
    horodatage_carte = models.BigIntegerField(
        verbose_name="Horodatage carte (ms)",
        help_text="Timestamp epoch en millisecondes transmis par la carte.",
    )

    class Meta:
        verbose_name = "Journal de scan"
        verbose_name_plural = "Journaux de scan"
        ordering = ["-cree_le"]
        indexes = [
            models.Index(fields=["uid"]),
            models.Index(fields=["cree_le"]),
        ]

    def __str__(self):
        return f"Scan {self.uid} @ {self.cree_le:%Y-%m-%d %H:%M:%S}"
