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

API_BASE = "http://127.0.0.1:8000"
ENDPOINT_SCAN = f"{API_BASE}/api/iot/scan/"
CERTS_DIR = Path("certs/cards")  # clés privées générées par P3 (seed_data)

SERVICE_TERMINAL = {
    "restaurant":   "RESTO-01",
    "bibliotheque": "BIBLIO-01",
    "transport":    "TRANSP-01",
}

def charger_cartes(chemin="cartes.json"):
    with open(chemin, "r") as f:
        return json.load(f)

def charger_cle_privee(uid):
    """Charge la clé privée PEM générée par P3 pour cette carte."""
    chemin = CERTS_DIR / f"{uid}.pem"
    if not chemin.exists():
        return None
    with open(chemin, "r") as f:
        return f.read()

def signer_nonce(cle_privee_pem, nonce_hex):
    """Signe le nonce avec la clé privée RSA de la carte."""
    import base64
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    cle = serialization.load_pem_private_key(
        cle_privee_pem.encode("utf-8"), password=None
    )
    nonce_bytes = bytes.fromhex(nonce_hex)
    signature = cle.sign(nonce_bytes, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")

def simuler_evenement(carte):
    services = carte["services_autorises"]
    service = random.choice(services)
    terminal_id = SERVICE_TERMINAL.get(service, "RESTO-01")

    nonce_hex = secrets.token_hex(32)
    timestamp_ms = int(time.time() * 1000)

    print(f"\n--- Terminal RFID (RC522 simulé) ---")
    print(f"Carte      : {carte['uid']} ({carte['prenom']} {carte['nom']})")
    print(f"Service    : {service} → terminal {terminal_id}")
    print(f"Nonce      : {nonce_hex[:16]}...")

    # Essai avec signature RSA si la clé privée existe
    cle_privee = charger_cle_privee(carte["uid"])
    if cle_privee:
        signature = signer_nonce(cle_privee, nonce_hex)
        print(f"Signature  : ✅ RSA générée")
    else:
        # Mode dégradé : pas de clé privée disponible (P3 pas encore lancé)
        signature = "SIGNATURE_MANQUANTE"
        print(f"Signature  : ⚠️  clé privée absente — mode mock")

    payload = {
        "uid": carte["uid"],
        "terminal_id": terminal_id,
        "timestamp": timestamp_ms,
        "nonce": nonce_hex,
        "signature": signature,
        "type": "identification",
    }

    print(f"Payload    : {json.dumps(payload, indent=2)}")

    try:
        reponse = requests.post(ENDPOINT_SCAN, json=payload, timeout=5)
        print(f"Statut HTTP: {reponse.status_code}")
        print(f"Réponse    : {reponse.json()}")
        return reponse.json()
    except requests.exceptions.ConnectionError:
        print("Résultat   : ⚠️  API non disponible — mode mock activé")
        return {"status": "mock", "message": "API P3 non disponible"}

if __name__ == "__main__":
    cartes = charger_cartes()
    carte = random.choice(cartes)
    simuler_evenement(carte)
