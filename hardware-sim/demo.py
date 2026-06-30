"""
Script de demo pour la soutenance — P2 Hardware
Envoie 5 transactions en direct, avec un rythme lisible pour le jury.
"""
import time
from simulateur_terminal import charger_cartes, simuler_evenement

PAUSE_ENTRE_SCANS = 2.5  # secondes, pour laisser le temps au jury de suivre

def lancer_demo():
    print("=" * 50)
    print(" DEMO SMART CAMPUS — Module Hardware (P2)")
    print("=" * 50)

    cartes = charger_cartes()
    scenario = [
        (cartes[0], "restaurant"),
        (cartes[1], "transport"),
        (cartes[2], "restaurant"),
        (cartes[3], "transport"),
        (cartes[4], "restaurant"),
    ]

    for i, (carte, service) in enumerate(scenario, start=1):
        print(f"\n>>> Scan {i}/{len(scenario)}")
        resultat = simuler_evenement(carte, service=service, verbose=True)

        if resultat["ok"]:
            print(">>> Transaction validee par le serveur.")
        else:
            print(f">>> Transaction refusee ou serveur indisponible "
                  f"({resultat['status_code']}).")

        if i < len(scenario):
            time.sleep(PAUSE_ENTRE_SCANS)

    print("\n" + "=" * 50)
    print(" FIN DE LA DEMO HARDWARE")
    print("=" * 50)

if __name__ == "__main__":
    lancer_demo()
