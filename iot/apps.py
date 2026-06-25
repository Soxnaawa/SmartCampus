from django.apps import AppConfig


class IotConfig(AppConfig):
    """Réception et vérification des scans de carte (MQTT / HTTP)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "iot"
    verbose_name = "IoT (scans de carte)"
