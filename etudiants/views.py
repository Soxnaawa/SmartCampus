"""Vues d'administration des fiches étudiants (CRUD réservé aux rôles habilités)."""
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from comptes.permissions import EstAdmin, EstCaissierOuAdmin

from .models import Etudiant
from .serializers import EtudiantResumeSerializer, EtudiantSerializer


@extend_schema(tags=["Étudiants"])
class EtudiantViewSet(viewsets.ModelViewSet):
    """CRUD des étudiants.

    - Lecture (list/retrieve) : caissier ou admin.
    - Écriture (create/update/delete) : admin uniquement.
    """

    queryset = Etudiant.objects.all().order_by("-cree_le")
    lookup_field = "uid_carte"
    lookup_value_regex = "[^/]+"  # autorise les tirets dans l'UID (SC-2025-...)

    def get_serializer_class(self):
        if self.action == "list":
            return EtudiantResumeSerializer
        return EtudiantSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [EstCaissierOuAdmin()]
        return [EstAdmin()]
