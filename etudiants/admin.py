"""Administration Django des étudiants."""
from django.contrib import admin

from .models import Etudiant


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    """Admin étudiant. Les noms restent chiffrés en base ; on affiche l'UID,
    la filière et le statut. Le nom complet déchiffré est consultable en détail
    via un champ calculé en lecture seule."""

    list_display = ("uid_carte", "filiere", "statut", "email", "cree_le")
    list_filter = ("statut", "filiere")
    search_fields = ("uid_carte", "email")
    readonly_fields = ("id", "cree_le", "nom_complet_affiche")
    exclude = ("nom_chiffre", "prenom_chiffre", "matricule_chiffre")

    @admin.display(description="Nom complet (déchiffré)")
    def nom_complet_affiche(self, obj):
        try:
            return obj.nom_complet
        except Exception:
            return "(déchiffrement impossible)"
