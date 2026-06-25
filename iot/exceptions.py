"""
Exceptions métier de la vérification de scan.

Ce sont des `APIException` DRF : levées dans les services, elles sont
automatiquement transformées en réponses HTTP avec le bon code de statut et un
corps JSON ``{"detail": ..., "code": ...}``. Le code applicatif (`default_code`)
permet au frontend de réagir précisément.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class DonneesScanInvalides(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Données de scan invalides ou incomplètes."
    default_code = "scan_invalide"


class CarteIntrouvable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Aucune carte ne correspond à cet UID."
    default_code = "carte_introuvable"


class CarteInactive(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "La carte n'est pas active (suspendue ou bloquée)."
    default_code = "carte_inactive"


class TerminalIntrouvable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Terminal inconnu."
    default_code = "terminal_introuvable"


class TerminalInactif(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Terminal désactivé."
    default_code = "terminal_inactif"


class HorodatageInvalide(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Horodatage du scan expiré ou incohérent."
    default_code = "horodatage_invalide"


class SignatureInvalide(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Signature de la carte invalide."
    default_code = "signature_invalide"


class RejeuDetecte(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Nonce déjà utilisé : tentative de rejeu détectée."
    default_code = "rejeu_detecte"


class SoldeInsuffisant(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Solde insuffisant pour effectuer le débit."
    default_code = "solde_insuffisant"
