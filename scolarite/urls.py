"""Routes scolarité (préfixées par /api/scolarite/ dans core.urls)."""
from django.urls import path

from .views import ExonererView, PayerView, RecuView, StatutView

urlpatterns = [
    path("payer/", PayerView.as_view(), name="scolarite-payer"),
    path("statut/<str:uid>/", StatutView.as_view(), name="scolarite-statut"),
    path("recu/<uuid:id>/", RecuView.as_view(), name="scolarite-recu"),
    path("exonerer/", ExonererView.as_view(), name="scolarite-exonerer"),
]
