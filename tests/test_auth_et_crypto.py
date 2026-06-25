"""Tests de l'authentification JWT et du chiffrement applicatif."""
import pytest

from core.crypto import chiffrer, dechiffrer
from etudiants.models import Etudiant, StatutCarte

pytestmark = pytest.mark.django_db


# ----- Authentification -----
def test_login_renvoie_tokens_et_role(api_client, admin_user):
    reponse = api_client.post(
        "/api/auth/login/",
        {"username": admin_user.username, "password": "motdepasse123"},
        format="json",
    )
    assert reponse.status_code == 200
    assert "access" in reponse.data and "refresh" in reponse.data
    assert reponse.data["role"] == "admin"


def test_me_retourne_le_profil(client_auth, caissier_user):
    reponse = client_auth(caissier_user).get("/api/auth/me/")
    assert reponse.status_code == 200
    assert reponse.data["username"] == caissier_user.username
    assert reponse.data["role"] == "caissier"


def test_mauvais_mot_de_passe_refuse(api_client, admin_user):
    reponse = api_client.post(
        "/api/auth/login/",
        {"username": admin_user.username, "password": "faux"},
        format="json",
    )
    assert reponse.status_code == 401


# ----- Chiffrement -----
def test_chiffrement_aller_retour():
    clair = "Diop Awa — données sensibles"
    blob = chiffrer(clair)
    assert blob != clair  # bien chiffré
    assert dechiffrer(blob) == clair


def test_chiffrement_detecte_l_alteration():
    blob = chiffrer("secret")
    altere = blob[:-2] + ("AA" if not blob.endswith("AA") else "BB")
    with pytest.raises(ValueError):
        dechiffrer(altere)


def test_donnees_etudiant_stockees_chiffrees():
    e = Etudiant(
        uid_carte="SC-2025-07777",
        email="x@test.sn",
        filiere="DIC2",
        statut=StatutCarte.ACTIF,
        certificat_pub="cert",
    )
    e.nom = "Ndiaye"
    e.save()
    # La colonne stocke le blob chiffré, pas le nom en clair.
    assert e.nom_chiffre != "Ndiaye"
    # La propriété déchiffre correctement.
    rechargé = Etudiant.objects.get(pk=e.pk)
    assert rechargé.nom == "Ndiaye"
