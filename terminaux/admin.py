"""Administration Django des terminaux."""
from django.contrib import admin

from .models import Terminal


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "libelle", "actif", "cree_le")
    list_filter = ("type", "actif")
    search_fields = ("code", "libelle")
