"""Serializers de l'app comptes (auth JWT + profil)."""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Utilisateur


class JetonAvecRoleSerializer(TokenObtainPairSerializer):
    """Ajoute le rôle (et quelques infos) dans le payload du token et dans la
    réponse de login, pour éviter au frontend un aller-retour supplémentaire."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        donnees = super().validate(attrs)
        donnees["role"] = self.user.role
        donnees["username"] = self.user.username
        donnees["user_id"] = str(self.user.id)
        return donnees


class UtilisateurSerializer(serializers.ModelSerializer):
    """Profil renvoyé par `/api/auth/me/`."""

    role_libelle = serializers.CharField(source="get_role_display", read_only=True)
    # UID de la carte si l'utilisateur est un étudiant lié à une fiche.
    uid_carte = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_libelle",
            "uid_carte",
            "is_active",
            "date_joined",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_uid_carte(self, obj) -> str | None:
        fiche = getattr(obj, "fiche_etudiant", None)
        return fiche.uid_carte if fiche else None


class DeconnexionSerializer(serializers.Serializer):
    """Entrée du logout : le refresh token à blacklister."""

    refresh = serializers.CharField()


# ----- Serializers de documentation (réponses) -----
class ReponseConnexionSerializer(serializers.Serializer):
    """Réponse de /api/auth/login/ (documentation OpenAPI)."""

    access = serializers.CharField(help_text="JWT d'accès (durée 15 min).")
    refresh = serializers.CharField(help_text="JWT de rafraîchissement.")
    role = serializers.CharField()
    username = serializers.CharField()
    user_id = serializers.UUIDField()


class MessageSerializer(serializers.Serializer):
    """Réponse générique { detail: ... } (documentation OpenAPI)."""

    detail = serializers.CharField()
