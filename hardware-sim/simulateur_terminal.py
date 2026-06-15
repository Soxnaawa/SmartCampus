import json
import random
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "smartcampus/terminal/transaction"

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

def publier_mqtt(message):
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        payload = json.dumps(message)
        result = client.publish(MQTT_TOPIC, payload)
        client.disconnect()
        if result.rc == 0:
            return {"status": "ok", "message": "Transaction publiée sur MQTT"}
        else:
            return {"status": "erreur", "message": "Échec publication MQTT"}
    except Exception:
        return {"status": "mock", "message": "Broker MQTT non disponible — mode mock activé"}

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

    print(f"\n--- Terminal RFID (RC522 simulé) ---")
    print(f"Carte      : {carte['uid']} ({carte['prenom']} {carte['nom']})")
    print(f"Service    : {service}")
    print(f"Type       : {type_evenement}")
    print(f"Montant    : {montant} FCFA")
    print(f"Topic MQTT : {MQTT_TOPIC}")
    print(f"Payload    : {json.dumps(message, indent=2)}")

    reponse = publier_mqtt(message)
    print(f"Résultat   : {reponse['message']}")
    return reponse

if __name__ == "__main__":
    cartes = charger_cartes()
    carte = random.choice(cartes)
    simuler_evenement(carte)
