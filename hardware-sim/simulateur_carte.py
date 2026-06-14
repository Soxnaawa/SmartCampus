import json
import random

def charger_cartes(chemin="cartes.json"):
    with open(chemin, "r") as f:
        return json.load(f)

def afficher_carte(carte):
    print(f"\n--- Carte détectée ---")
    print(f"UID        : {carte['uid']}")
    print(f"Étudiant   : {carte['prenom']} {carte['nom']}")
    print(f"Solde      : {carte['solde']} FCFA")
    print(f"Services   : {', '.join(carte['services_autorises'])}")

if __name__ == "__main__":
    cartes = charger_cartes()
    carte = random.choice(cartes)
    afficher_carte(carte)
