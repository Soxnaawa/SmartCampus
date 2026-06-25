"""Administration Django de la scolarité."""
from django.contrib import admin

from .models import PaiementScolarite


@admin.register(PaiementScolarite)
class PaiementScolariteAdmin(admin.ModelAdmin):
    list_display = (
        "cree_le",
        "etudiant",
        "type_periode",
        "periode_couverte",
        "montant",
        "statut",
        "caissier",
    )
    list_filter = ("type_periode", "statut")
    search_fields = ("etudiant__uid_carte", "periode_couverte")
    date_hierarchy = "cree_le"
    readonly_fields = ("cree_le",)
