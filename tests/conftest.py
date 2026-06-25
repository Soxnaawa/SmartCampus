"""Fixtures partagées par la suite de tests."""
import secrets
import time

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from comptes.models import Role
from core.signatures import generer_paire_et_certificat, signer_nonce
from etudiants.models import Etudiant, StatutCarte
from monetique.models import Solde
from terminaux.models import Terminal, TypeTerminal

Utilisateur = get_user_model()


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_auth(api_client):
    """Renvoie une fonction qui authentifie le client pour un utilisateur."""

    def _auth(utilisateur):
        api_client.force_authenticate(user=utilisateur)
        return api_client

    return _auth


# ---------------------------------------------------------------------------
# Utilisateurs par rôle
# ---------------------------------------------------------------------------
def _creer_utilisateur(username, role, password="motdepasse123"):
    u = Utilisateur.objects.create(
        username=username, email=f"{username}@test.sn", role=role
    )
    u.set_password(password)
    u.save()
    return u


@pytest.fixture
def admin_user(db):
    return _creer_utilisateur("admin_t", Role.ADMIN)


@pytest.fixture
def caissier_user(db):
    return _creer_utilisateur("caissier_t", Role.CAISSIER)


@pytest.fixture
def controleur_user(db):
    return _creer_utilisateur("controleur_t", Role.CONTROLEUR)


@pytest.fixture
def etudiant_user(db):
    return _creer_utilisateur("etudiant_t", Role.ETUDIANT)


# ---------------------------------------------------------------------------
# Carte / étudiant / terminal
# ---------------------------------------------------------------------------
@pytest.fixture
def paire_cles():
    """Paire (clé privée PEM, certificat PEM) d'une carte de test."""
    priv, cert = generer_paire_et_certificat("SC-2025-00001")
    return {"priv": priv, "cert": cert}


@pytest.fixture
def etudiant(db, paire_cles, etudiant_user):
    e = Etudiant(
        uid_carte="SC-2025-00001",
        email="awa.diop@test.sn",
        filiere="DIC2 — M1 Génie Logiciel",
        statut=StatutCarte.ACTIF,
        certificat_pub=paire_cles["cert"],
        compte=etudiant_user,
    )
    e.nom = "Diop"
    e.prenom = "Awa"
    e.matricule = "MAT2025001"
    e.save()
    Solde.objects.create(etudiant=e, montant=100_000)  # 1 000 FCFA
    return e


@pytest.fixture
def terminal(db):
    return Terminal.objects.create(
        code="RESTO-01", type=TypeTerminal.RESTAURANT, libelle="Restaurant"
    )


# ---------------------------------------------------------------------------
# Constructeur d'enveloppe de scan signée
# ---------------------------------------------------------------------------
@pytest.fixture
def construire_scan():
    """Fabrique un message de scan signé valide (paramétrable)."""

    def _build(uid, terminal_code, priv, *, montant=None, nonce=None, timestamp=None):
        nonce = nonce or secrets.token_hex(32)
        timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
        payload = {
            "uid": uid,
            "terminal_id": terminal_code,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signer_nonce(priv, nonce),
        }
        if montant is not None:
            payload["montant"] = montant
        return payload

    return _build
