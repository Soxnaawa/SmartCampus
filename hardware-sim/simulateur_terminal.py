"""
Simulateur de terminal RFID — P2 Hardware
Compatible avec l'API P3 (Django REST + signature RSA)
Endpoint : POST /api/iot/scan/
"""
import json
import random
import secrets
import time
import requests
from pathlib import Path

API_BASE = "https://subcerebellar-chalcographic-sawyer.ngrok-free.dev"
ENDPOINT_SCAN = f"{API_BASE}/api/iot/scan/"
CERTS_DIR = Path("certs/cards")  # cles privees generees par P3 (seed_data)

SERVICE_TERMINAL = {
    "restaurant":   "RESTO-01",
    "transport":    "BUS-01",
}

def charger_cartes(chemin="cartes.json"):
    with open(chemin, "r") as f:
        return json.load(f)

def charger_cle_privee(uid):
    """Charge la cle privee PEM generee par P3 pour cette carte."""
    chemin = CERTS_DIR / f"{uid}.pem"
    if not chemin.exists():
        return None
    with open(chemin, "r") as f:
        return f.read()

def signer_nonce(cle_privee_pem, nonce_hex):
    """Signe le nonce avec la cle privee RSA de la carte."""
    import base64
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    cle = serialization.load_pem_private_key(
        cle_privee_pem.encode("utf-8"), password=None
    )
    nonce_bytes = bytes.fromhex(nonce_hex)
    signature = cle.sign(nonce_bytes, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")

def construire_payload(carte, service=None, verbose=True):
    """Construit et signe un payload de scan pour une carte donnee."""
    services_dispo = [s for s in carte["services_autorises"] if s in SERVICE_TERMINAL]
    if not services_dispo:
        services_dispo = ["restaurant"]
    if service is None or service not in services_dispo:
        service = random.choice(services_dispo)
    terminal_id = SERVICE_TERMINAL[service]

    nonce_hex = secrets.token_hex(32)
    timestamp_ms = int(time.time() * 1000)

    cle_privee = charger_cle_privee(carte["uid"])
    if cle_privee:
        signature = signer_nonce(cle_privee, nonce_hex)
        sig_statut = "[OK] RSA generee"
    else:
        signature = "SIGNATURE_MANQUANTE"
        sig_statut = "[ABSENT] cle privee absente -- mode mock"

    if verbose:
        print(f"\n--- Terminal RFID (RC522 simule) ---")
        print(f"Carte      : {carte['uid']} ({carte['prenom']} {carte['nom']})")
        print(f"Service    : {service} -> terminal {terminal_id}")
        print(f"Nonce      : {nonce_hex[:16]}...")
        print(f"Signature  : {sig_statut}")

    return {
        "uid": carte["uid"],
        "terminal_id": terminal_id,
        "timestamp": timestamp_ms,
        "nonce": nonce_hex,
        "signature": signature,
        "type": "identification",
    }

def envoyer_scan(payload, verbose=True):
    """Envoie un payload de scan a l'API P3 et gere les erreurs proprement."""
    if verbose:
        print(f"Payload    : {json.dumps(payload, indent=2)}")
    try:
        reponse = requests.post(ENDPOINT_SCAN, json=payload, timeout=5)
        try:
            corps = reponse.json()
        except ValueError:
            corps = {"detail": reponse.text}

        if verbose:
            print(f"Statut HTTP: {reponse.status_code}")
            print(f"Reponse    : {corps}")

        return {
            "ok": reponse.status_code == 200,
            "status_code": reponse.status_code,
            "body": corps,
        }
    except requests.exceptions.ConnectionError:
        if verbose:
            print("Resultat   : API non disponible -- mode mock active")
        return {"ok": False, "status_code": None, "body": {"detail": "API P3 non disponible"}}

def simuler_evenement(carte, service=None, verbose=True):
    """Construit, signe et envoie un scan pour une carte. Fonction principale reutilisable."""
    payload = construire_payload(carte, service=service, verbose=verbose)
    return envoyer_scan(payload, verbose=verbose)


JWT_CAISSIER = None

def se_connecter(username, password):
    """Se connecte a l'API et recupere un token JWT (access)."""
    url = f"{API_BASE}/api/auth/login/"
    try:
        reponse = requests.post(url, json={"username": username, "password": password}, timeout=5)
        if reponse.status_code == 200:
            data = reponse.json()
            print(f"Connexion reussie pour {username}")
            return data.get("access")
        else:
            print(f"Echec connexion ({reponse.status_code}): {reponse.json()}")
            return None
    except requests.exceptions.ConnectionError:
        print("API non disponible")
        return None

def simuler_controle(carte, service="restaurant", verbose=True):
    payload = construire_payload(carte, service=service, verbose=False)
    payload["type"] = "controle"
    if verbose:
        print(f"\n--- Controle (acces/scolarite) ---")
        print(f"Carte   : {carte['uid']} ({carte['prenom']} {carte['nom']})")
        print(f"Payload : {json.dumps(payload, indent=2)}")
    return envoyer_scan(payload, verbose=verbose)

def simuler_debit(carte, montant=500, service="restaurant", verbose=True):
    terminal_id = SERVICE_TERMINAL.get(service, "RESTO-01")
    nonce_hex = secrets.token_hex(32)
    timestamp_ms = int(time.time() * 1000)
    cle_privee = charger_cle_privee(carte["uid"])
    signature = signer_nonce(cle_privee, nonce_hex) if cle_privee else "SIGNATURE_MANQUANTE"
    payload = {
        "uid": carte["uid"], "terminal_id": terminal_id, "timestamp": timestamp_ms,
        "nonce": nonce_hex, "signature": signature, "montant": montant,
    }
    if verbose:
        print(f"\n--- Debit (paiement) ---")
        print(f"Carte   : {carte['uid']} ({carte['prenom']} {carte['nom']})")
        print(f"Montant : {montant} FCFA -> terminal {terminal_id}")
        print(f"Payload : {json.dumps(payload, indent=2)}")
    headers = {}
    if JWT_CAISSIER:
        headers["Authorization"] = f"Bearer {JWT_CAISSIER}"
    url = f"{API_BASE}/api/transaction/debit/"
    try:
        reponse = requests.post(url, json=payload, headers=headers, timeout=5)
        try:
            corps = reponse.json()
        except ValueError:
            corps = {"detail": reponse.text}
        if verbose:
            print(f"Statut HTTP: {reponse.status_code}")
            print(f"Reponse    : {corps}")
        return {"ok": reponse.status_code in (200, 201), "status_code": reponse.status_code, "body": corps}
    except requests.exceptions.ConnectionError:
        if verbose:
            print("API non disponible")
        return {"ok": False, "status_code": None, "body": {"detail": "API non disponible"}}

def simuler_credit(carte, montant=2000, verbose=True):
    payload = {"uid": carte["uid"], "montant": montant}
    if verbose:
        print(f"\n--- Credit (recharge) ---")
        print(f"Carte   : {carte['uid']} ({carte['prenom']} {carte['nom']})")
        print(f"Montant : +{montant} FCFA")
        print(f"Payload : {json.dumps(payload, indent=2)}")
    headers = {}
    if JWT_CAISSIER:
        headers["Authorization"] = f"Bearer {JWT_CAISSIER}"
    url = f"{API_BASE}/api/transaction/credit/"
    try:
        reponse = requests.post(url, json=payload, headers=headers, timeout=5)
        try:
            corps = reponse.json()
        except ValueError:
            corps = {"detail": reponse.text}
        if verbose:
            print(f"Statut HTTP: {reponse.status_code}")
            print(f"Reponse    : {corps}")
        return {"ok": reponse.status_code in (200, 201), "status_code": reponse.status_code, "body": corps}
    except requests.exceptions.ConnectionError:
        if verbose:
            print("API non disponible")
        return {"ok": False, "status_code": None, "body": {"detail": "API non disponible"}}



if __name__ == "__main__":
    cartes = charger_cartes()
    carte = random.choice(cartes)
    simuler_evenement(carte)
