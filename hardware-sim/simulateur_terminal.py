import json
import random
import requests
from datetime import datetime
import uuid

API_URL = "http://localhost:8000"

def charger_cartes(chemin="cartes.json"):
    with open(chemin, "r") as f:
        return json.load(f)

def construire_message(carte, type_evenement, service, montant):
    return {
        "uid": carte["uid"],
        "type": type_evenement,
        "service": service,
        "montant": montant,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "nonce": uuid.uuid4().hex[:12]
    }

def envoyer_transaction(message):
    try:
        response = requests.post(f"{API_URL}/auth/carte", json=message, timeout=5)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"status": "erreur", "message": "API non disponible — mode mock activé", "autorise": True}

def simuler_evenement(carte):
    services_disponibles = carte["services_autorises"]
    service = random.choice(services_disponibles)

    if service == "restaurant":
        type_evenement = "paiement"
        montant = random.randint(500, 2000)
    elif service == "transport":
        type_evenement = "paiement"
        montant = 200
    else:
        type_evenement = "acces"
        montant = 0

    message = construire_message(carte, type_evenement, service, montant)
    print(f"\n--- Terminal RFID ---")
    print(f"Carte      : {carte['uid']} ({carte['prenom']} {carte['nom']})")
    print(f"Service    : {service}")
    print(f"Type       : {type_evenement}")
    print(f"Montant    : {montant} FCFA")
    print(f"Envoi vers : {API_URL}/auth/carte ...")

    reponse = envoyer_transaction(message)
    print(f"Réponse    : {reponse.get('message', reponse)}")
    return reponse

if __name__ == "__main__":
    cartes = charger_cartes()
    carte = random.choice(cartes)
    simuler_evenement(carte)
