"""Vues monétiques : débit, crédit, solde, historique, blocage, stats."""
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import EstAdmin, EstCaissierOuAdmin
from etudiants.models import Etudiant
from terminaux.models import Terminal

from .models import Solde, StatutTransaction, Transaction, TypeTransaction
from .serializers import (
    BloquerCarteSerializer,
    CreditSerializer,
    DebitSerializer,
    ReponseBlocageSerializer,
    ReponseDashboardSerializer,
    SoldeSerializer,
    TransactionSerializer,
)
from .services import bloquer_carte, crediter, debiter, statistiques_dashboard


# ---------------------------------------------------------------------------
# Aides communes
# ---------------------------------------------------------------------------
def _etudiant_par_uid(uid: str) -> Etudiant:
    etudiant = Etudiant.objects.filter(uid_carte=uid).first()
    if etudiant is None:
        raise Http404("Aucun étudiant pour cet UID.")
    return etudiant


def _verifier_acces_donnees(user, etudiant: Etudiant) -> None:
    """Un étudiant n'accède qu'à SES données ; l'admin accède à tout."""
    if user.est_admin:
        return
    if user.est_etudiant:
        fiche = getattr(user, "fiche_etudiant", None)
        if fiche and fiche.pk == etudiant.pk:
            return
    raise PermissionDenied("Vous ne pouvez consulter que vos propres données.")


# ---------------------------------------------------------------------------
# Débit / Crédit
# ---------------------------------------------------------------------------
@extend_schema(
    tags=["Monétique"],
    summary="Débiter une carte (caissier + signature carte)",
    description="Vérifie l'enveloppe signée par la carte (nonce, signature RSA, "
    "horodatage) puis débite le solde de façon atomique. Renvoie 201 si validé, "
    "402 si solde insuffisant (transaction tracée), 409 en cas de rejeu de nonce.",
    request=DebitSerializer,
    responses={201: TransactionSerializer, 402: TransactionSerializer},
    examples=[
        OpenApiExample(
            "Débit signé",
            value={
                "uid": "SC-2025-00001",
                "terminal_id": "RESTO-01",
                "timestamp": 1718450000000,
                "nonce": "a1b2…(hex)",
                "signature": "Base64Signature==",
                "montant": 15000,
            },
            request_only=True,
        )
    ],
)
class DebitView(APIView):
    """POST /api/transaction/debit/ — débite une carte (caissier + signature)."""

    permission_classes = [EstCaissierOuAdmin]

    def post(self, request):
        serializer = DebitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        montant = donnees.pop("montant")

        # `debiter` lève une exception métier si la vérification échoue,
        # sinon renvoie la transaction (valide ou refusée pour solde).
        tx = debiter(donnees, montant=montant)

        corps = TransactionSerializer(tx).data
        if tx.statut == StatutTransaction.REFUSE:
            return Response(corps, status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(corps, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Monétique"],
    summary="Recharger un solde (caissier ou admin)",
    description="Recharge au guichet : pas de signature carte requise. Crée une "
    "transaction de crédit et incrémente le solde de façon atomique.",
    request=CreditSerializer,
    responses={201: TransactionSerializer},
)
class CreditView(APIView):
    """POST /api/transaction/credit/ — recharge un solde (admin/caissier)."""

    permission_classes = [EstCaissierOuAdmin]

    def post(self, request):
        serializer = CreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        etudiant = _etudiant_par_uid(donnees["uid"])
        terminal = None
        if donnees.get("terminal_id"):
            terminal = get_object_or_404(Terminal, code=donnees["terminal_id"])

        tx = crediter(
            etudiant=etudiant,
            montant=donnees["montant"],
            terminal=terminal,
            type_transaction=TypeTransaction.CREDIT,
            metadata=donnees.get("metadata"),
        )
        return Response(
            TransactionSerializer(tx).data, status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# Consultation solde / historique
# ---------------------------------------------------------------------------
@extend_schema(
    tags=["Monétique"],
    summary="Consulter le solde d'une carte",
    description="Accessible à l'étudiant propriétaire ou à un administrateur.",
    responses={200: SoldeSerializer},
)
class SoldeView(APIView):
    """GET /api/solde/<uid>/ — consulter le solde (étudiant le sien / admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, uid):
        etudiant = _etudiant_par_uid(uid)
        _verifier_acces_donnees(request.user, etudiant)
        solde, _ = Solde.objects.get_or_create(etudiant=etudiant)
        return Response(SoldeSerializer(solde).data)


@extend_schema(
    tags=["Monétique"],
    summary="Historique des transactions (paginé)",
    description="Liste paginée des transactions d'une carte. Accessible à "
    "l'étudiant propriétaire ou à un administrateur. Filtres optionnels.",
    parameters=[
        OpenApiParameter("type", str, description="debit | credit | remboursement"),
        OpenApiParameter("statut", str, description="valide | refuse | suspect | annule"),
        OpenApiParameter("date_debut", str, description="Date min (AAAA-MM-JJ)."),
        OpenApiParameter("date_fin", str, description="Date max (AAAA-MM-JJ)."),
    ],
)
class HistoriqueView(ListAPIView):
    """GET /api/transactions/<uid>/ — historique paginé + filtres date/type."""

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        etudiant = _etudiant_par_uid(self.kwargs["uid"])
        _verifier_acces_donnees(self.request.user, etudiant)

        qs = Transaction.objects.filter(etudiant=etudiant).select_related(
            "terminal"
        )

        params = self.request.query_params
        type_tx = params.get("type")
        if type_tx:
            qs = qs.filter(type=type_tx)
        statut = params.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        date_debut = params.get("date_debut")
        if date_debut:
            qs = qs.filter(cree_le__date__gte=date_debut)
        date_fin = params.get("date_fin")
        if date_fin:
            qs = qs.filter(cree_le__date__lte=date_fin)

        return qs.order_by("-cree_le")


# ---------------------------------------------------------------------------
# Blocage de carte / tableau de bord
# ---------------------------------------------------------------------------
@extend_schema(
    tags=["Monétique"],
    summary="Bloquer une carte (admin)",
    request=BloquerCarteSerializer,
    responses={200: ReponseBlocageSerializer},
)
class BloquerCarteView(APIView):
    """POST /api/carte/bloquer/ — bloque une carte (admin)."""

    permission_classes = [EstAdmin]

    def post(self, request):
        serializer = BloquerCarteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        etudiant = _etudiant_par_uid(serializer.validated_data["uid"])
        bloquer_carte(etudiant)
        return Response(
            {
                "uid": etudiant.uid_carte,
                "statut": etudiant.statut,
                "detail": "Carte bloquée.",
            }
        )


@extend_schema(
    tags=["Monétique"],
    summary="Tableau de bord — KPIs globaux (admin)",
    responses={200: ReponseDashboardSerializer},
)
class DashboardView(APIView):
    """GET /api/stats/dashboard/ — KPIs globaux (admin)."""

    permission_classes = [EstAdmin]

    def get(self, request):
        return Response(statistiques_dashboard())
