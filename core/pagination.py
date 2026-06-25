"""Pagination standard de l'API (utilisée notamment par l'historique)."""
from rest_framework.pagination import PageNumberPagination


class PaginationStandard(PageNumberPagination):
    """Pagination par numéro de page, taille ajustable via `?page_size=`."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
