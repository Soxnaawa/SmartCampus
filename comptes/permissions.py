"""
Permissions DRF basées sur le rôle de l'utilisateur.

Chaque endpoint déclare la (ou les) classe(s) de permission attendue(s). Les
permissions s'appuient exclusivement sur `Utilisateur.role` (voir comptes.models)
afin de garder une logique centralisée et testable.
"""
from rest_framework.permissions import BasePermission


class _RoleBase(BasePermission):
    """Permission générique : exige un utilisateur authentifié dont un attribut
    booléen de rôle est vrai."""

    attribut_role: str = ""
    message = "Votre rôle ne permet pas cette action."

    def has_permission(self, request, view):
        utilisateur = request.user
        if not (utilisateur and utilisateur.is_authenticated):
            return False
        return bool(getattr(utilisateur, self.attribut_role, False))


class EstAdmin(_RoleBase):
    attribut_role = "est_admin"
    message = "Réservé aux administrateurs."


class EstCaissier(_RoleBase):
    attribut_role = "est_caissier"
    message = "Réservé aux caissiers."


class EstControleur(_RoleBase):
    attribut_role = "est_controleur"
    message = "Réservé aux contrôleurs."


class EstEtudiant(_RoleBase):
    attribut_role = "est_etudiant"
    message = "Réservé aux étudiants."


class EstCaissierOuAdmin(BasePermission):
    """Caissier OU administrateur (ex : recharge de solde)."""

    message = "Réservé aux caissiers ou administrateurs."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.est_caissier or u.est_admin))


class EstControleurOuAdmin(BasePermission):
    message = "Réservé aux contrôleurs ou administrateurs."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.est_controleur or u.est_admin))
