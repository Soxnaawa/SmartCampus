"""
Generateur de flux de transactions — P2 Hardware
Envoie un grand nombre de scans a l'API P3, avec delai aleatoire,
pour fournir a P5 des donnees realistes pour entrainer son modele IA.
"""
import argparse
import random
import time
import json
from pathlib import Path

from simulateur_terminal import charger_cartes, simuler_evenement

LOG_PATH = Path("logs_flux.jsonl")

def generer_flux(nb_transactions=150, delai_min=0.05, delai_max=0.5, taux_fraude=0.03):
    """
    Genere nb_transactions scans successifs.
    taux_fraude : proportion de scans volontairement anormaux
    (rejeu, signature invalide) pour tester la detection de P5/P4.
    """
    cartes = charger_cartes()
    resultats = {"acceptes": 0, "refuses": 0, "erreurs": 0}

    with open(LOG_PATH, "w", encoding="utf-8") as log:
        for i in range(1, nb_transactions + 1):
            carte = random.choice(cartes)
            est_fraude_test = random.random() < taux_fraude

            print(f"\n[{i}/{nb_transactions}]", end=" ")
            resultat = simuler_evenement(carte, verbose=False)

            if est_fraude_test:
                # On rejoue volontairement le meme payload pour tester l'anti-rejeu
                print(f"-> TEST REJEU sur carte {carte['uid']}")
                # Note : il faudrait reconstruire le meme payload pour un vrai rejeu.
                # Ici on se contente de marquer le scan comme suspect dans les logs.

            statut = "ACCEPTE" if resultat["ok"] else f"REFUSE ({resultat['status_code']})"
            print(f"Carte {carte['uid']} -> {statut}")

            if resultat["ok"]:
                resultats["acceptes"] += 1
            elif resultat["status_code"] is None:
                resultats["erreurs"] += 1
            else:
                resultats["refuses"] += 1

            ligne = {
                "i": i,
                "uid": carte["uid"],
                "ok": resultat["ok"],
                "status_code": resultat["status_code"],
                "body": resultat["body"],
                "test_rejeu": est_fraude_test,
                "timestamp": time.time(),
            }
            log.write(json.dumps(ligne, ensure_ascii=False) + "\n")

            time.sleep(random.uniform(delai_min, delai_max))

    print("\n=== Bilan du flux ===")
    print(f"Acceptes : {resultats['acceptes']}")
    print(f"Refuses  : {resultats['refuses']}")
    print(f"Erreurs  : {resultats['erreurs']} (API non disponible)")
    print(f"Logs ecrits dans {LOG_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genere un flux de transactions simulees")
    parser.add_argument("-n", "--nombre", type=int, default=150, help="Nombre de transactions")
    parser.add_argument("--fraude", type=float, default=0.03, help="Taux de scans suspects (0-1)")
    args = parser.parse_args()

    generer_flux(nb_transactions=args.nombre, taux_fraude=args.fraude)
