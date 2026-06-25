"""Serializers de l'app étudiants (gestion administrative des fiches)."""
from rest_framework import serializers

from .models import Etudiant


class EtudiantSerializer(serializers.ModelSerializer):
    """Fiche étudiant complète (usage administratif).

    Les champs `nom`, `prenom`, `matricule` sont exposés en clair : ils
    correspondent aux propriétés du modèle qui chiffrent/déchiffrent
    automatiquement vers les colonnes `*_chiffre`. Ce serializer ne doit servir
    qu'aux rôles autorisés (admin/caissier), jamais au contrôle public.
    """

    # Déclarés explicitement car ce ne sont pas des champs de modèle mais des
    # propriétés (avec getter/setter) gérant le chiffrement.
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    matricule = serializers.CharField(max_length=50)

    class Meta:
        model = Etudiant
        fields = [
            "id",
            "uid_carte",
            "nom",
            "prenom",
            "matricule",
            "email",
            "filiere",
            "statut",
            "certificat_pub",
            "compte",
            "cree_le",
        ]
        read_only_fields = ["id", "cree_le"]
        extra_kwargs = {
            # Le certificat est volumineux ; on l'accepte en écriture mais on
            # ne le renvoie pas dans les listes pour alléger les réponses.
            "certificat_pub": {"write_only": False},
            "compte": {"required": False},
        }


class EtudiantResumeSerializer(serializers.ModelSerializer):
    """Vue allégée d'un étudiant (sans données chiffrées) pour les listes."""

    class Meta:
        model = Etudiant
        fields = ["id", "uid_carte", "filiere", "statut", "cree_le"]
        read_only_fields = fields
