from django.apps import AppConfig


class ComptesConfig(AppConfig):
    """Utilisateurs, rôles et authentification JWT."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "comptes"
    verbose_name = "Comptes & rôles"
