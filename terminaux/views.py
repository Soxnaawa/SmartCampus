"""Vues de gestion des terminaux."""
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from comptes.permissions import EstAdmin
from rest_framework.permissions import IsAuthenticated

from .models import Terminal
from .serializers import TerminalSerializer


@extend_schema(tags=["Terminaux"])
class TerminalViewSet(viewsets.ModelViewSet):
    """CRUD des terminaux.

    - Lecture : tout utilisateur authentifié (les terminaux ne sont pas secrets).
    - Écriture : admin uniquement.
    """

    queryset = Terminal.objects.all().order_by("code")
    serializer_class = TerminalSerializer
    lookup_field = "code"
    lookup_value_regex = "[^/]+"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [EstAdmin()]
