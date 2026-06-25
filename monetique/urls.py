"""Routes monétiques (incluses sous /api/ dans core.urls).

Donne : /api/transaction/debit/, /api/transaction/credit/, /api/solde/<uid>/,
/api/transactions/<uid>/, /api/carte/bloquer/, /api/stats/dashboard/.
"""
from django.urls import path

from .views import (
    BloquerCarteView,
    CreditView,
    DashboardView,
    DebitView,
    HistoriqueView,
    SoldeView,
)

# Un UID contient des tirets (SC-2025-00147) : on capture tout sauf le slash.
UID = "<str:uid>"

urlpatterns = [
    path("transaction/debit/", DebitView.as_view(), name="transaction-debit"),
    path("transaction/credit/", CreditView.as_view(), name="transaction-credit"),
    path(f"solde/{UID}/", SoldeView.as_view(), name="solde-detail"),
    path(f"transactions/{UID}/", HistoriqueView.as_view(), name="transactions-liste"),
    path("carte/bloquer/", BloquerCarteView.as_view(), name="carte-bloquer"),
    path("stats/dashboard/", DashboardView.as_view(), name="stats-dashboard"),
]
