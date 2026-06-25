"""Vues d'authentification JWT et profil utilisateur."""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    DeconnexionSerializer,
    JetonAvecRoleSerializer,
    MessageSerializer,
    ReponseConnexionSerializer,
    UtilisateurSerializer,
)


@extend_schema(
    tags=["Authentification"],
    summary="Connexion (obtenir un couple de tokens)",
    description="Authentifie un utilisateur et renvoie un token d'accès "
    "(15 min) + un token de rafraîchissement, avec son rôle.",
    responses={200: ReponseConnexionSerializer},
)
class ConnexionView(TokenObtainPairView):
    """POST /api/auth/login/ → access + refresh (avec le rôle dans le payload)."""

    serializer_class = JetonAvecRoleSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"  # anti-bruteforce


@extend_schema(
    tags=["Authentification"],
    summary="Rafraîchir le token d'accès",
)
class RafraichirView(TokenRefreshView):
    """POST /api/auth/refresh/ → nouvel access token à partir d'un refresh."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"


@extend_schema(
    tags=["Authentification"],
    summary="Déconnexion (blacklist du refresh token)",
    request=DeconnexionSerializer,
    responses={205: OpenApiResponse(MessageSerializer, description="Déconnecté.")},
)
class DeconnexionView(APIView):
    """POST /api/auth/logout/ → blacklist du refresh token fourni."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeconnexionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            jeton = RefreshToken(serializer.validated_data["refresh"])
            jeton.blacklist()
        except TokenError:
            # Token déjà invalide/expiré : on considère la déconnexion réussie.
            return Response(
                {"detail": "Token déjà invalide ou expiré."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        return Response(
            {"detail": "Déconnexion réussie."},
            status=status.HTTP_205_RESET_CONTENT,
        )


@extend_schema(
    tags=["Authentification"],
    summary="Profil de l'utilisateur connecté",
    responses={200: UtilisateurSerializer},
)
class MoiView(APIView):
    """GET /api/auth/me/ → profil de l'utilisateur connecté."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)
