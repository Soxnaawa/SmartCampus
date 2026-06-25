"""Serializers de l'app IoT (enveloppe de scan signée)."""
from rest_framework import serializers

from .models import JournalScan, TypeScan


class ScanSerializer(serializers.Serializer):
    """Message de scan reçu par /api/iot/scan/ (équivalent HTTP du MQTT)."""

    uid = serializers.CharField(max_length=20)
    terminal_id = serializers.CharField(max_length=20)
    timestamp = serializers.IntegerField(help_text="Epoch en millisecondes.")
    nonce = serializers.CharField(max_length=64)
    signature = serializers.CharField()
    # Type optionnel ; défaut = simple identification.
    type = serializers.ChoiceField(
        choices=TypeScan.choices, required=False, default=TypeScan.IDENTIFICATION
    )


class ReponseScanSerializer(serializers.Serializer):
    """Réponse d'un scan accepté (documentation)."""

    accepte = serializers.BooleanField()
    uid = serializers.CharField()
    filiere = serializers.CharField()
    statut_carte = serializers.CharField()
    terminal = serializers.CharField()
    type_scan = serializers.CharField()
    scan_id = serializers.UUIDField(allow_null=True)


class JournalScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalScan
        fields = [
            "id",
            "uid",
            "terminal",
            "type_scan",
            "horodatage_carte",
            "cree_le",
        ]
        read_only_fields = fields
