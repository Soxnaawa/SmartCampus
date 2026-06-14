# Hardware Simulation — P2

Ce dossier simule le comportement physique d'un terminal RFID et de cartes étudiantes sans matériel réel.

## Fichiers

- `cartes.json` : 20 cartes étudiantes fictives (uid, nom, solde, services)
- `simulateur_carte.py` : charge et affiche une carte aléatoire
- `simulateur_terminal.py` : simule un terminal qui lit une carte et envoie une requête à l'API P3

## Lancer

```bash
python simulateur_carte.py
python simulateur_terminal.py
```

## Comment le vrai hardware s'intègrerait

En production, le lecteur RFID RC522 connecté à un Arduino/ESP32 lirait l'UID de la carte physique.
Le microcontrôleur enverrait ensuite le même format JSON que ce simulateur via WiFi + MQTT vers le serveur.
Le format du message reste identique — seule la couche de lecture change (RC522 → script Python).
