"""Routes IoT (préfixées par /api/iot/ dans core.urls)."""
from django.urls import path

from .views import ScanView

urlpatterns = [
    path("scan/", ScanView.as_view(), name="iot-scan"),
]
