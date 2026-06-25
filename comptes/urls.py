"""Routes d'authentification (préfixées par /api/auth/ dans core.urls)."""
from django.urls import path

from .views import ConnexionView, DeconnexionView, MoiView, RafraichirView

urlpatterns = [
    path("login/", ConnexionView.as_view(), name="auth-login"),
    path("refresh/", RafraichirView.as_view(), name="auth-refresh"),
    path("logout/", DeconnexionView.as_view(), name="auth-logout"),
    path("me/", MoiView.as_view(), name="auth-me"),
]
