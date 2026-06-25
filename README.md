# Smart Campus — Backend (module P3)

API REST du système universitaire **Smart Campus** (ESP/UCAD). Gère la carte
étudiante RFID/NFC : identification, porte-monnaie électronique (restaurant,
reprographie, transport), et preuve de paiement de scolarité lors des contrôles.

> Périmètre P3 : **uniquement le backend**. Le hardware est simulé ; les scans
> de carte arrivent par MQTT (équipe P2). Les autres modules (sécurité avancée,
> IA anti-fraude, frontend) sont développés séparément et consomment cette API.

---

## Sommaire
- [Stack technique](#stack-technique)
- [Architecture](#architecture)
- [Installation locale](#installation-locale)
- [Lancement via Docker](#lancement-via-docker)
- [Données de test (seed)](#données-de-test-seed)
- [Tests](#tests)
- [Simuler un scan de carte](#simuler-un-scan-de-carte)
- [Endpoints de l'API](#endpoints-de-lapi)
- [Sécurité](#sécurité)
- [Choix techniques notables](#choix-techniques-notables)

---

## Stack technique
- **Python 3.12+**, **Django 5.x**, **Django REST Framework**
- **PostgreSQL** (`psycopg[binary]`) — SQLite par défaut en local/tests
- **JWT** via `djangorestframework-simplejwt` (access 15 min, refresh + blacklist)
- **CORS** via `django-cors-headers`
- **Chiffrement** AES-256-GCM + RSA/X.509 via `cryptography`
- **MQTT** via `paho-mqtt` (réception des scans)
- **PDF** des reçus via `reportlab`
- **Tests** avec `pytest-django`
- Conteneurisation : `Dockerfile` + `docker-compose.yml` (Django + PostgreSQL +
  Redis + Mosquitto)

## Architecture
```
core/        settings, urls racine, chiffrement (AES-256-GCM), signatures X.509,
             modèle de base (UUID), commande seed_data
comptes/     Utilisateur custom (rôles étudiant/caissier/contrôleur/admin) + auth JWT
etudiants/   modèle Étudiant (nom/prénom/matricule chiffrés) + certificat de carte
terminaux/   terminaux physiques (restaurant, reprographie, transport, …)
monetique/   soldes + transactions, débit atomique, vérification de signature carte
scolarite/   paiements de scolarité + calcul dynamique du statut + reçu PDF
iot/         vérification des scans (anti-rejeu) + endpoint HTTP + listener MQTT
```

Tous les montants sont des **entiers en centimes de FCFA** (jamais de float).
Toutes les clés primaires sont des **UUID**.

---

## Installation locale

Prérequis : Python 3.12+.

```bash
# 1. Environnement virtuel
python -m venv .venv
# Windows PowerShell :
.venv\Scripts\Activate.ps1
# Linux/macOS :
source .venv/bin/activate

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env          # puis adapter au besoin
# Générer une clé de chiffrement (recommandé) :
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# … et la coller dans CHAMP_CHIFFREMENT_CLE du .env

# 4. Base de données (SQLite par défaut si DATABASE_URL absente)
python manage.py migrate

# 5. Données de test + comptes
python manage.py seed_data

# 6. Lancer le serveur
python manage.py runserver
```

API disponible sur http://127.0.0.1:8000/ — healthcheck : `/api/sante/`,
admin Django : `/admin/`.

Pour recevoir les scans MQTT (dans un second terminal) :
```bash
python manage.py mqtt_listener
```

### Variables d'environnement
Voir [`.env.example`](.env.example). Les principales :

| Variable | Rôle | Défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | clé secrète Django | dev |
| `DJANGO_DEBUG` | mode debug | `False` |
| `DATABASE_URL` | base de données | SQLite local |
| `CHAMP_CHIFFREMENT_CLE` | clé AES-256 (base64, 32 o) | dérivée de SECRET_KEY (dev) |
| `JWT_ALGORITHM` | `HS256` ou `RS256` | `HS256` |
| `CORS_ALLOWED_ORIGINS` | origines frontend | localhost:3000/5173 |
| `MQTT_HOST` / `MQTT_PORT` | broker MQTT | localhost / 1883 |
| `MQTT_TOPIC_SCAN` | topic des scans | `campus/reader/scan` |
| `SCAN_TTL_SECONDES` | fraîcheur d'un scan | 30 |

---

## Lancement via Docker

```bash
# (optionnel) générer une clé de chiffrement et la mettre dans un .env
docker compose up --build
```

Démarre 5 services : `db` (PostgreSQL), `redis`, `mosquitto`, `web` (API,
port 8000) et `mqtt_listener`. Les migrations sont appliquées automatiquement,
et `seed_data` est exécuté au premier démarrage (`SEED_ON_START=1`).

---

## Données de test (seed)
```bash
python manage.py seed_data           # crée si la base est vide
python manage.py seed_data --vider   # purge puis régénère
```
Génère ~30 étudiants (données chiffrées), leurs **paires de clés / certificats
X.509** (clés privées dans `certs/cards/<uid>.pem` pour pouvoir simuler des
scans signés), des soldes, un historique de transactions, et des paiements de
scolarité produisant des statuts variés (à jour, en retard, exonéré).



---

## Tests
```bash
pytest
```
Couvre : calcul du statut de scolarité (tous les cas), débit atomique,
rejet d'un nonce rejoué, rejet d'une signature invalide, expiration de
l'horodatage, permissions par rôle, chiffrement (aller-retour + détection
d'altération) et authentification JWT. Les tests tournent sur SQLite (aucune
configuration requise).

---

## Simuler un scan de carte
Après un `seed_data` (qui génère les clés privées de test) :
```bash
# Affiche un message signé valide (à utiliser en curl) :
python manage.py simuler_scan --uid SC-2025-00001 --terminal RESTO-01

# … ou le publie directement sur le broker MQTT :
python manage.py simuler_scan --uid SC-2025-00001 --terminal RESTO-01 --mqtt
```
Exemple d'appel HTTP de secours :
```bash
curl -X POST http://127.0.0.1:8000/api/iot/scan/ \
     -H "Content-Type: application/json" \
     -d '{"uid":"SC-2025-00001","terminal_id":"RESTO-01","timestamp":...,"nonce":"...","signature":"..."}'
```

---

## Documentation de l'API
La documentation est **générée automatiquement** depuis le code (drf-spectacular),
donc toujours à jour. Une fois le serveur lancé :

| Format | URL |
|---|---|
| Swagger UI (interactif, « Try it out ») | http://127.0.0.1:8000/api/docs/ |
| ReDoc (lecture) | http://127.0.0.1:8000/api/redoc/ |
| Schéma OpenAPI 3 brut | http://127.0.0.1:8000/api/schema/ |

Dans Swagger UI : faire **Authorize** et coller `Bearer <access>` (token obtenu
via `/api/auth/login/`) pour tester les endpoints protégés.

Documents versionnés dans le dépôt :
- Référence lisible : [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- Schéma figé : [`docs/openapi.yaml`](docs/openapi.yaml) — régénérable via
  `python manage.py spectacular --file docs/openapi.yaml`


## Endpoints de l'API
Préfixe commun : **`/api/`** (sans numéro de version). Réponses en JSON.

### Authentification — `comptes`
| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/auth/login/` | access + refresh token | public |
| POST | `/api/auth/refresh/` | rafraîchir le token | public |
| POST | `/api/auth/logout/` | blacklist du refresh | authentifié |
| GET | `/api/auth/me/` | profil courant | authentifié |

### Monétique — `monetique`
| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/transaction/debit/` | débiter une carte | caissier/admin + signature carte |
| POST | `/api/transaction/credit/` | recharger un solde | caissier/admin |
| GET | `/api/solde/<uid>/` | consulter un solde | étudiant (le sien) / admin |
| GET | `/api/transactions/<uid>/` | historique paginé (filtres `type`, `statut`, `date_debut`, `date_fin`) | étudiant (le sien) / admin |
| POST | `/api/carte/bloquer/` | bloquer une carte | admin |
| GET | `/api/stats/dashboard/` | KPIs globaux | admin |

### Scolarité — `scolarite`
| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/scolarite/payer/` | enregistrer un paiement | caissier |
| GET | `/api/scolarite/statut/<uid>/` | statut pour le contrôle (contrat figé) | contrôleur/admin |
| GET | `/api/scolarite/recu/<id>/` | reçu PDF | étudiant (le sien) / admin |
| POST | `/api/scolarite/exonerer/` | marquer exonéré | admin |

### IoT — `iot`
| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/iot/scan/` | scan HTTP (équivalent MQTT) | signature carte |

### Référentiels
| Méthode | URL | Description | Accès |
|---|---|---|---|
| `*` | `/api/etudiants/` | CRUD étudiants | lecture caissier/admin, écriture admin |
| `*` | `/api/terminaux/` | CRUD terminaux | lecture authentifié, écriture admin |

Format **figé** de `/api/scolarite/statut/<uid>/` :
```json
{
  "uid": "SC-2025-00147",
  "filiere": "DIC2 — M1",
  "statut": "a_jour",
  "derniere_periode": "2025-11",
  "mois_de_retard": 0,
  "token_valide": true
}
```
`statut` ∈ `a_jour` | `en_retard` | `exonere`. Aucune donnée nominative ou
financière n'est exposée à ce endpoint (confidentialité du contrôle public).

---

## Sécurité
- **ORM exclusif** (pas de SQL brut → anti-injection).
- **JWT** : access 15 min, refresh rotatif avec blacklist au logout ; `HS256`
  par défaut, `RS256` disponible (`manage.py generer_cles_jwt`).
- **Permissions DRF strictes par rôle** ; un étudiant n'accède qu'à ses données.
- **Données personnelles chiffrées au repos** (AES-256-GCM), clé en variable
  d'environnement.
- **Anti-rejeu** : nonce à usage unique (journalisé), horodatage à TTL court,
  signature RSA du nonce vérifiée via le certificat X.509 de la carte.
- **Débit atomique** : `transaction.atomic()` + `select_for_update()` + verrou
  optimiste (`version`) → pas de double-débit.
- **CORS** restreint aux origines du frontend.
- **Validation stricte** des entrées via les serializers DRF + throttling sur
  le login et les scans.

## Choix techniques notables
Quelques décisions prises là où le cahier des charges laissait le choix (toutes
signalées en commentaire dans le code) :
- `core` sert à la fois de package de configuration et d'app utilitaire (base
  abstraite, chiffrement, `seed_data`).
- L'endpoint `/api/iot/scan/` n'est pas protégé par JWT mais par la **signature
  de la carte** (les terminaux n'ont pas de compte).
- L'anti-rejeu repose sur une table-journal unique (`iot.JournalScan`, colonne
  `nonce` UNIQUE) ; la colonne `nonce` des transactions sert de filet de sécurité.
- Le **régime de scolarité** (mensuel/semestriel) est déduit des paiements de
  l'étudiant ; en semestriel, `mois_de_retard` = nombre de semestres dus × 6.
- Un débit refusé pour solde insuffisant est **tracé** (transaction `refuse`,
  HTTP 402) plutôt que silencieusement ignoré.
