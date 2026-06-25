from django.apps import AppConfig


class MonetiqueConfig(AppConfig):
    """Soldes, transactions et paiements de services."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "monetique"
    verbose_name = "Monétique"
