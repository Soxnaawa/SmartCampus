"""Modèle Étudiant : carte RFID, données personnelles chiffrées, certificat."""
from django.conf import settings
from django.db import models

from core.crypto import chiffrer, dechiffrer
from core.models import ModeleBase


class StatutCarte(models.TextChoices):
    """État de la carte étudiante."""

    ACTIF = "actif", "Actif"
    SUSPENDU = "suspendu", "Suspendu"
    BLOQUE = "bloque", "Bloqué"


class Etudiant(ModeleBase):
    """Fiche étudiant rattachée à une carte unique.

    Les données personnelles (nom, prénom, matricule) sont stockées chiffrées
    en AES-256-GCM dans les colonnes `*_chiffre`. On expose des propriétés
    `nom`, `prenom`, `matricule` qui chiffrent/déchiffrent à la volée :
        etu.nom = "Diop"        # chiffre et range dans nom_chiffre
        print(etu.nom)          # déchiffre nom_chiffre
    """

    uid_carte = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="UID de la carte",
        help_text="Identifiant unique de la carte physique, ex : SC-2025-00147.",
    )

    # --- Données personnelles chiffrées au repos (texte = blob base64) ---
    nom_chiffre = models.TextField(verbose_name="Nom (chiffré)")
    prenom_chiffre = models.TextField(verbose_name="Prénom (chiffré)")
    matricule_chiffre = models.TextField(verbose_name="Matricule (chiffré)")

    email = models.EmailField(max_length=255, unique=True)
    filiere = models.CharField(max_length=100, verbose_name="Filière")

    statut = models.CharField(
        max_length=10,
        choices=StatutCarte.choices,
        default=StatutCarte.ACTIF,
        verbose_name="Statut de la carte",
    )

    certificat_pub = models.TextField(
        verbose_name="Certificat X.509 (PEM)",
        help_text="Certificat de la carte, utilisé pour vérifier les signatures.",
    )

    # Compte de connexion associé (pour qu'un étudiant consulte SES données).
    compte = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fiche_etudiant",
        verbose_name="Compte de connexion",
    )

    class Meta:
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"
        ordering = ["-cree_le"]

    def __str__(self):
        # On évite d'exposer le nom en clair dans les logs/admin par défaut.
        return f"{self.uid_carte} ({self.filiere})"

    # ----- Propriétés déchiffrées à la volée -----
    @property
    def nom(self) -> str:
        return dechiffrer(self.nom_chiffre)

    @nom.setter
    def nom(self, valeur: str):
        self.nom_chiffre = chiffrer(valeur)

    @property
    def prenom(self) -> str:
        return dechiffrer(self.prenom_chiffre)

    @prenom.setter
    def prenom(self, valeur: str):
        self.prenom_chiffre = chiffrer(valeur)

    @property
    def matricule(self) -> str:
        return dechiffrer(self.matricule_chiffre)

    @matricule.setter
    def matricule(self, valeur: str):
        self.matricule_chiffre = chiffrer(valeur)

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}".strip()

    @property
    def carte_active(self) -> bool:
        return self.statut == StatutCarte.ACTIF
