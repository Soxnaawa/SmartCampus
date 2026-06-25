from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App `core` : héberge la base abstraite, les utilitaires de chiffrement
    et la commande de génération de données de test (`seed_data`)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Cœur (base, chiffrement, outils)"
