"""Serializers de l'app terminaux."""
from rest_framework import serializers

from .models import Terminal


class TerminalSerializer(serializers.ModelSerializer):
    type_libelle = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Terminal
        fields = [
            "id",
            "code",
            "type",
            "type_libelle",
            "libelle",
            "actif",
            "cree_le",
        ]
        read_only_fields = ["id", "cree_le"]
