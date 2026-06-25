from django.apps import AppConfig


class ScolariteConfig(AppConfig):
    """Paiements de scolarité et calcul du statut."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "scolarite"
    verbose_name = "Scolarité"
