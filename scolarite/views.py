"""Vues de l'app scolarité : payer, statut (contrôle), reçu PDF, exonérer."""
from django.http import Http404, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import EstAdmin, EstCaissier, EstControleurOuAdmin
from etudiants.models import Etudiant

from .models import PaiementScolarite, StatutPaiement, TypePeriode
from .pdf import generer_recu_pdf
from .serializers import (
    ExonererSerializer,
    PaiementScolariteSerializer,
    PayerSerializer,
    StatutScolariteSerializer,
)
from .services import statut_pour_controle


def _etudiant_par_uid(uid: str) -> Etudiant:
    etudiant = Etudiant.objects.filter(uid_carte=uid).first()
    if etudiant is None:
        raise Http404("Aucun étudiant pour cet UID.")
    return etudiant


@extend_schema(
    tags=["Scolarité"],
    summary="Enregistrer un paiement de scolarité (caissier)",
    request=PayerSerializer,
    responses={201: PaiementScolariteSerializer},
)
class PayerView(APIView):
    """POST /api/scolarite/payer/ — enregistre un paiement (caissier)."""

    permission_classes = [EstCaissier]

    def post(self, request):
        serializer = PayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        etudiant = _etudiant_par_uid(donnees["uid"])

        paiement = PaiementScolarite.objects.create(
            etudiant=etudiant,
            type_periode=donnees["type_periode"],
            periode_couverte=donnees["periode_couverte"],
            montant=donnees["montant"],
            caissier=request.user,
            statut=StatutPaiement.VALIDE,
        )
        return Response(
            PaiementScolariteSerializer(paiement).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Scolarité"],
    summary="Statut de scolarité pour le contrôle (contrôleur/admin)",
    description="Contrat de sortie FIGÉ. Ne renvoie que les champs publics du "
    "contrôle : aucune donnée nominative ni financière. `statut` ∈ a_jour | "
    "en_retard | exonere.",
    responses={200: StatutScolariteSerializer},
)
class StatutView(APIView):
    """GET /api/scolarite/statut/<uid>/ — statut pour le contrôle (contrôleur).

    Renvoie STRICTEMENT le contrat figé : aucun nom, aucune info financière.
    """

    permission_classes = [EstControleurOuAdmin]

    def get(self, request, uid):
        etudiant = _etudiant_par_uid(uid)
        return Response(statut_pour_controle(etudiant))


@extend_schema(
    tags=["Scolarité"],
    summary="Télécharger le reçu PDF d'un paiement",
    description="Réservé à l'étudiant concerné ou à un administrateur. "
    "Renvoie un fichier PDF (application/pdf).",
    responses={
        (200, "application/pdf"): OpenApiResponse(
            OpenApiTypes.BINARY, description="Le reçu au format PDF."
        )
    },
)
class RecuView(APIView):
    """GET /api/scolarite/recu/<id>/ — télécharge le reçu PDF (étudiant le sien)."""

    # Authentification requise ; l'autorisation fine (admin OU étudiant
    # propriétaire) est gérée dans get().
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        paiement = PaiementScolarite.objects.filter(id=id).select_related(
            "etudiant"
        ).first()
        if paiement is None:
            raise Http404("Reçu introuvable.")

        utilisateur = request.user
        autorise = utilisateur.est_admin
        if not autorise and utilisateur.est_etudiant:
            fiche = getattr(utilisateur, "fiche_etudiant", None)
            autorise = fiche is not None and fiche.pk == paiement.etudiant_id
        if not autorise:
            raise PermissionDenied("Ce reçu ne vous appartient pas.")

        pdf = generer_recu_pdf(paiement)
        reponse = HttpResponse(pdf, content_type="application/pdf")
        reponse["Content-Disposition"] = (
            f'attachment; filename="{paiement.numero_recu}.pdf"'
        )
        return reponse


@extend_schema(
    tags=["Scolarité"],
    summary="Marquer un étudiant exonéré (admin)",
    request=ExonererSerializer,
    responses={201: PaiementScolariteSerializer},
)
class ExonererView(APIView):
    """POST /api/scolarite/exonerer/ — marque un étudiant exonéré (admin)."""

    permission_classes = [EstAdmin]

    def post(self, request):
        serializer = ExonererSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        etudiant = _etudiant_par_uid(donnees["uid"])

        paiement = PaiementScolarite.objects.create(
            etudiant=etudiant,
            type_periode=TypePeriode.EXONERATION,
            periode_couverte=donnees.get("periode_couverte", ""),
            montant=donnees.get("montant", 0),  # 0 autorisé pour une exonération
            caissier=request.user,
            statut=StatutPaiement.VALIDE,
        )
        return Response(
            PaiementScolariteSerializer(paiement).data,
            status=status.HTTP_201_CREATED,
        )
