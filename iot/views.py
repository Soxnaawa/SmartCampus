"""Vue HTTP de réception d'un scan (équivalent de secours au flux MQTT)."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ReponseScanSerializer, ScanSerializer
from .services import verifier_scan


@extend_schema(
    tags=["IoT"],
    summary="Recevoir un scan de carte (signé)",
    description="Équivalent HTTP du flux MQTT. Pas de JWT : l'authentification "
    "est la signature de la carte. Rejette les nonces rejoués (409), les "
    "signatures invalides (400), les horodatages expirés (400) et les cartes "
    "inactives (403).",
    request=ScanSerializer,
    responses={200: ReponseScanSerializer},
)
class ScanView(APIView):
    """POST /api/iot/scan/ — reçoit et vérifie un scan de carte.

    Décision signalée : l'authentification de cet endpoint n'est PAS un JWT mais
    la **signature de la carte** elle-même (les terminaux n'ont pas de compte).
    On laisse donc l'accès ouvert (`AllowAny`) mais chaque requête est rejetée
    si la signature/horodatage/nonce ne sont pas valides (voir verifier_scan).
    Un throttling dédié limite la cadence.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # pas de JWT : auth assurée par la signature
    throttle_scope = "scan"

    def post(self, request):
        serializer = ScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        type_scan = donnees.pop("type")

        # Lève une APIException métier (code HTTP adapté) si invalide.
        resultat = verifier_scan(donnees, type_scan=type_scan, consommer=True)

        return Response(
            {
                "accepte": True,
                "uid": resultat.etudiant.uid_carte,
                "filiere": resultat.etudiant.filiere,
                "statut_carte": resultat.etudiant.statut,
                "terminal": resultat.terminal.code,
                "type_scan": type_scan,
                "scan_id": str(resultat.journal.id) if resultat.journal else None,
            },
            status=status.HTTP_200_OK,
        )
