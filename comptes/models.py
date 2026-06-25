"""Modèle utilisateur personnalisé avec 4 rôles métier."""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """Les quatre rôles du système (cahier des charges §3)."""

    ETUDIANT = "etudiant", "Étudiant"
    CAISSIER = "caissier", "Caissier"
    CONTROLEUR = "controleur", "Contrôleur"
    ADMIN = "admin", "Administrateur"


class Utilisateur(AbstractUser):
    """Utilisateur du backend.

    On étend `AbstractUser` (username/password/email gérés par Django) en
    ajoutant un identifiant UUID et un champ `role` qui pilote toutes les
    permissions DRF. La liaison vers la fiche étudiant se fait depuis
    `etudiants.Etudiant.compte` (relation inverse `fiche_etudiant`).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifiant",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ETUDIANT,
        verbose_name="Rôle",
    )
    # On rend l'email obligatoire et unique : utile pour les comptes réels.
    email = models.EmailField("adresse e-mail", unique=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # ----- Aides de lecture des rôles (utilisées par les permissions) -----
    @property
    def est_admin(self) -> bool:
        # Un superuser Django est considéré administrateur du métier.
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def est_caissier(self) -> bool:
        return self.role == Role.CAISSIER

    @property
    def est_controleur(self) -> bool:
        return self.role == Role.CONTROLEUR

    @property
    def est_etudiant(self) -> bool:
        return self.role == Role.ETUDIANT
