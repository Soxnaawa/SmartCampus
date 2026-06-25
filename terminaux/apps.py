from django.apps import AppConfig


class TerminauxConfig(AppConfig):
    """Terminaux physiques (restaurant, reprographie, transport...)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "terminaux"
    verbose_name = "Terminaux"
