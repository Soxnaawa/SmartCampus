"""Routes de gestion des étudiants : /api/etudiants/..."""
from rest_framework.routers import DefaultRouter

from .views import EtudiantViewSet

router = DefaultRouter()
router.register(r"etudiants", EtudiantViewSet, basename="etudiant")

urlpatterns = router.urls
