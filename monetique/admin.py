"""Administration Django de la monétique."""
from django.contrib import admin

from .models import Solde, Transaction


@admin.register(Solde)
class SoldeAdmin(admin.ModelAdmin):
    list_display = ("etudiant", "montant", "version", "mis_a_jour")
    search_fields = ("etudiant__uid_carte",)
    readonly_fields = ("mis_a_jour", "version")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "cree_le",
        "etudiant",
        "terminal",
        "type",
        "montant",
        "statut",
        "score_fraude",
    )
    list_filter = ("type", "statut")
    search_fields = ("etudiant__uid_carte", "nonce")
    readonly_fields = ("cree_le",)
    date_hierarchy = "cree_le"
