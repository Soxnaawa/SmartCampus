"""
URLs racine du projet Smart Campus.

Convention imposée (§5) : préfixe `/api/` SANS numéro de version.
Chaque app métier expose ses propres routes, incluses ici.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def sante(_request):
    """Endpoint de liveness/healthcheck (utilisé par docker-compose)."""
    return JsonResponse({"statut": "ok", "service": "smartcampus-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/sante/", sante, name="sante"),
    # --- Documentation OpenAPI ---
    # Schéma brut (OpenAPI 3) :
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Documentation interactive Swagger UI :
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Documentation ReDoc (lecture) :
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Authentification & comptes
    path("api/auth/", include("comptes.urls")),
    # Monétique : /api/transaction/, /api/solde/, /api/transactions/,
    #             /api/carte/, /api/stats/
    path("api/", include("monetique.urls")),
    # Scolarité : /api/scolarite/...
    path("api/scolarite/", include("scolarite.urls")),
    # IoT : /api/iot/scan/
    path("api/iot/", include("iot.urls")),
    # Référentiels : /api/etudiants/, /api/terminaux/
    path("api/", include("etudiants.urls")),
    path("api/", include("terminaux.urls")),
]
