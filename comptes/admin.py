"""Administration Django des comptes."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Admin utilisateur : on ajoute le champ `role` aux écrans standard."""

    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")

    # On réutilise les fieldsets de UserAdmin en insérant le rôle.
    fieldsets = UserAdmin.fieldsets + (("Rôle métier", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle métier", {"fields": ("role", "email")}),
    )
