"""Routes des terminaux : /api/terminaux/..."""
from rest_framework.routers import DefaultRouter

from .views import TerminalViewSet

router = DefaultRouter()
router.register(r"terminaux", TerminalViewSet, basename="terminal")

urlpatterns = router.urls
