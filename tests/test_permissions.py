"""Tests des permissions par rôle sur les endpoints (§7)."""
import pytest

pytestmark = pytest.mark.django_db


def test_dashboard_reserve_admin(client_auth, admin_user, etudiant_user):
    assert client_auth(admin_user).get("/api/stats/dashboard/").status_code == 200
    assert client_auth(etudiant_user).get("/api/stats/dashboard/").status_code == 403


def test_statut_controle_accessible_controleur_pas_caissier(
    client_auth, controleur_user, caissier_user, etudiant
):
    url = f"/api/scolarite/statut/{etudiant.uid_carte}/"
    assert client_auth(controleur_user).get(url).status_code == 200
    # Le caissier n'est pas habilité au contrôle de scolarité.
    assert client_auth(caissier_user).get(url).status_code == 403


def test_etudiant_voit_son_solde_pas_celui_des_autres(
    client_auth, etudiant, etudiant_user, admin_user
):
    url = f"/api/solde/{etudiant.uid_carte}/"
    # Le propriétaire y accède.
    assert client_auth(etudiant_user).get(url).status_code == 200

    # Un autre étudiant (non lié à cette fiche) est refusé.
    from django.contrib.auth import get_user_model

    autre = get_user_model().objects.create(
        username="autre_etu", email="autre@test.sn", role="etudiant"
    )
    assert client_auth(autre).get(url).status_code == 403

    # L'admin accède à tout.
    assert client_auth(admin_user).get(url).status_code == 200


def test_payer_scolarite_reserve_caissier(
    client_auth, caissier_user, controleur_user, etudiant
):
    corps = {
        "uid": etudiant.uid_carte,
        "type_periode": "mensuel",
        "periode_couverte": "2025-11",
        "montant": 5_000_000,
    }
    assert (
        client_auth(caissier_user).post(
            "/api/scolarite/payer/", corps, format="json"
        ).status_code
        == 201
    )
    assert (
        client_auth(controleur_user).post(
            "/api/scolarite/payer/", corps, format="json"
        ).status_code
        == 403
    )


def test_bloquer_carte_reserve_admin(
    client_auth, admin_user, caissier_user, etudiant
):
    corps = {"uid": etudiant.uid_carte}
    assert (
        client_auth(caissier_user).post(
            "/api/carte/bloquer/", corps, format="json"
        ).status_code
        == 403
    )
    reponse = client_auth(admin_user).post(
        "/api/carte/bloquer/", corps, format="json"
    )
    assert reponse.status_code == 200
    assert reponse.data["statut"] == "bloque"


def test_endpoint_non_authentifie_refuse(api_client, etudiant):
    assert api_client.get(f"/api/solde/{etudiant.uid_carte}/").status_code == 401
