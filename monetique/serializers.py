"""Serializers monétiques (validation stricte des entrées)."""
from rest_framework import serializers

from .models import Solde, Transaction


class EnveloppeScanSerializer(serializers.Serializer):
    """Champs communs à un message de scan signé par la carte (§6.a)."""

    uid = serializers.CharField(max_length=20)
    terminal_id = serializers.CharField(max_length=20)
    timestamp = serializers.IntegerField(help_text="Epoch en millisecondes.")
    nonce = serializers.CharField(max_length=64)
    signature = serializers.CharField()


class DebitSerializer(EnveloppeScanSerializer):
    """Entrée du débit : enveloppe signée + montant à débiter."""

    montant = serializers.IntegerField(
        min_value=1, help_text="Montant en centimes FCFA (> 0)."
    )


class CreditSerializer(serializers.Serializer):
    """Entrée de la recharge (pas de signature carte : opération guichet)."""

    uid = serializers.CharField(max_length=20)
    montant = serializers.IntegerField(min_value=1)
    terminal_id = serializers.CharField(max_length=20, required=False)
    metadata = serializers.JSONField(required=False)


class BloquerCarteSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=20)


class SoldeSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(source="etudiant.uid_carte", read_only=True)
    montant_fcfa = serializers.IntegerField(read_only=True)

    class Meta:
        model = Solde
        fields = ["uid", "montant", "montant_fcfa", "version", "mis_a_jour"]
        read_only_fields = fields


class ReponseBlocageSerializer(serializers.Serializer):
    """Réponse de /api/carte/bloquer/ (documentation)."""

    uid = serializers.CharField()
    statut = serializers.CharField()
    detail = serializers.CharField()


class ReponseDashboardSerializer(serializers.Serializer):
    """KPIs renvoyés par /api/stats/dashboard/ (documentation)."""

    etudiants_total = serializers.IntegerField()
    cartes_actives = serializers.IntegerField()
    cartes_bloquees = serializers.IntegerField()
    transactions_total = serializers.IntegerField()
    transactions_aujourdhui = serializers.IntegerField()
    repartition_statut = serializers.DictField(child=serializers.IntegerField())
    volume_debit_centimes = serializers.IntegerField()
    volume_credit_centimes = serializers.IntegerField()
    solde_total_centimes = serializers.IntegerField()


class TransactionSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(source="etudiant.uid_carte", read_only=True)
    terminal_code = serializers.CharField(
        source="terminal.code", read_only=True, default=None
    )
    type_libelle = serializers.CharField(source="get_type_display", read_only=True)
    statut_libelle = serializers.CharField(
        source="get_statut_display", read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "uid",
            "terminal_code",
            "type",
            "type_libelle",
            "montant",
            "statut",
            "statut_libelle",
            "score_fraude",
            "metadata",
            "cree_le",
        ]
        read_only_fields = fields
