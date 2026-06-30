# Hardware Simulation — P2

Ce dossier simule le comportement physique d'un terminal RFID et de cartes étudiantes
sans matériel réel. Chaque scan est signé en RSA et envoyé en HTTP vers l'API de P3.

## Fichiers

- `cartes.json` : 20 cartes étudiantes fictives (uid, nom, solde, services autorisés)
- `simulateur_carte.py` : charge et affiche une carte aléatoire
- `simulateur_terminal.py` : simule un scan signé (un seul, aléatoire) envoyé à l'API
- `generer_flux.py` : envoie en boucle un grand nombre de scans (pour générer des
  données pour le module IA de P5)
- `demo.py` : scénario fixe de 5 scans avec pauses, prévu pour la soutenance
- `certs/cards/` : clés privées RSA des cartes, fournies par P3 (généré par son
  `seed_data`). **Ce dossier est exclu de Git (voir `.gitignore` à la racine) —
  ne jamais le commiter.**
- `logs_flux.jsonl` : historique des envois de `generer_flux.py` (exclu de Git aussi)

## Prérequis

```bash
pip install requests cryptography
```

## Configuration : URL de l'API

Par défaut le script pointe vers un serveur local :

```python
API_BASE = "http://127.0.0.1:8000"
```

Si le serveur de P3 tourne sur une autre machine (réseau local ou ngrok), changer
cette ligne dans `simulateur_terminal.py` avec l'IP ou l'URL fournie par P3, par exemple :

```python
API_BASE = "lien ngrok en attente"
```

## Lancer

Un seul scan, aléatoire :
```bash
python simulateur_terminal.py
```

Générer un flux de transactions (pour P5) :
```bash
python generer_flux.py -n 150
```

Lancer la démo de soutenance (5 scans avec pauses) :
```bash
python demo.py
```

## Format du message envoyé à l'API

```json
{
  "uid": "SC-2025-00001",
  "terminal_id": "RESTO-01",
  "timestamp": 1718450000000,
  "nonce": "a3f2c1...(hex, 64 caracteres)",
  "signature": "base64...(signature RSA du nonce)",
  "type": "identification"
}
```

`terminal_id` doit correspondre à un terminal existant côté P3 : `RESTO-01`,
`RESTO-02` ou `BUS-01`.

## Comportement attendu

- Si `certs/cards/<uid>.pem` existe : la signature RSA est réelle (`[OK]`)
- Si le fichier n'existe pas : signature factice `SIGNATURE_MANQUANTE` (mode mock,
  utile pour tester sans les clés)
- Si l'API ne répond pas (serveur P3 éteint) : le script l'indique clairement et
  continue sans planter

## Comment le vrai hardware s'intégrerait

En production, le lecteur RFID RC522 connecté à un Arduino/ESP32 lirait l'UID de
la carte physique et la clé privée serait stockée de manière sécurisée sur la
carte elle-même (pas en fichier `.pem` local). Le microcontrôleur enverrait le
même format JSON que ce simulateur, via WiFi. Le format du message reste
identique — seule la couche de lecture et de stockage de la clé change.