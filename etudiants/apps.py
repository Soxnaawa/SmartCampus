from django.apps import AppConfig


class EtudiantsConfig(AppConfig):
    """Étudiants, cartes et certificats X.509."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "etudiants"
    verbose_name = "Étudiants & cartes"
