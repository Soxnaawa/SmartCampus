"""Serializers de l'app scolarité."""
import re

from rest_framework import serializers

from .models import PaiementScolarite, StatutPaiement, TypePeriode

# Formats acceptés pour `periode_couverte` : "2025-11" (mois) ou "2025-S1".
_RE_MOIS = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RE_SEMESTRE = re.compile(r"^\d{4}-S[12]$")


class PaiementScolariteSerializer(serializers.ModelSerializer):
    """Représentation d'un paiement (lecture)."""

    uid = serializers.CharField(source="etudiant.uid_carte", read_only=True)
    caissier_username = serializers.CharField(
        source="caissier.username", read_only=True, default=None
    )
    numero_recu = serializers.CharField(read_only=True)

    class Meta:
        model = PaiementScolarite
        fields = [
            "id",
            "uid",
            "type_periode",
            "periode_couverte",
            "montant",
            "statut",
            "caissier_username",
            "numero_recu",
            "cree_le",
        ]
        read_only_fields = fields


class PayerSerializer(serializers.Serializer):
    """Entrée de POST /api/scolarite/payer/."""

    uid = serializers.CharField(max_length=20)
    type_periode = serializers.ChoiceField(
        choices=[TypePeriode.MENSUEL, TypePeriode.SEMESTRIEL]
    )
    periode_couverte = serializers.CharField(max_length=7)
    montant = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        """Vérifie la cohérence entre le type de période et son format."""
        type_periode = attrs["type_periode"]
        periode = attrs["periode_couverte"]
        if type_periode == TypePeriode.MENSUEL and not _RE_MOIS.match(periode):
            raise serializers.ValidationError(
                {"periode_couverte": "Format mensuel attendu : AAAA-MM (ex : 2025-11)."}
            )
        if type_periode == TypePeriode.SEMESTRIEL and not _RE_SEMESTRE.match(periode):
            raise serializers.ValidationError(
                {"periode_couverte": "Format semestriel attendu : AAAA-S1 ou AAAA-S2."}
            )
        return attrs


class ExonererSerializer(serializers.Serializer):
    """Entrée de POST /api/scolarite/exonerer/."""

    uid = serializers.CharField(max_length=20)
    # Période couverte par l'exonération (ex : 2025-S1) ; libre / optionnelle.
    periode_couverte = serializers.CharField(max_length=7, required=False, default="")
    montant = serializers.IntegerField(min_value=0, required=False, default=0)


class StatutScolariteSerializer(serializers.Serializer):
    """Sérialise le contrat figé de /api/scolarite/statut/<uid>/.

    Sert surtout de documentation/validation du format de sortie.
    """

    uid = serializers.CharField()
    filiere = serializers.CharField()
    statut = serializers.ChoiceField(choices=["a_jour", "en_retard", "exonere"])
    derniere_periode = serializers.CharField(allow_null=True)
    mois_de_retard = serializers.IntegerField()
    token_valide = serializers.BooleanField()
