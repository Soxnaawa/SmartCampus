# Référence de l'API — Smart Campus (P3)

> Documentation **interactive** (toujours à jour, générée depuis le code) :
> - Swagger UI : `http://127.0.0.1:8000/api/docs/`
> - ReDoc : `http://127.0.0.1:8000/api/redoc/`
> - Schéma OpenAPI 3 brut : `http://127.0.0.1:8000/api/schema/`
> - Schéma figé (versionné dans le dépôt) : [`docs/openapi.yaml`](openapi.yaml)
>
> Ce fichier est un **résumé lisible**. En cas de doute, le schéma OpenAPI fait foi.

## Conventions générales
- **Base URL** : `http://127.0.0.1:8000` en local. Préfixe commun **`/api/`** (sans version).
- **Format** : JSON (sauf le reçu, qui est un PDF binaire).
- **Montants** : entiers en **centimes de FCFA** (750 FCFA → `75000`).
- **Identifiants** : UUID.
- **Authentification** : JWT Bearer. Récupérer un token via `POST /api/auth/login/`,
  puis l'envoyer dans l'en-tête `Authorization: Bearer <access>`.

### Rôles
`etudiant` · `caissier` · `controleur` · `admin`. Chaque endpoint exige un rôle
précis ; un rôle insuffisant renvoie **403**. Un étudiant n'accède qu'à **ses**
données.

### Codes d'erreur courants
| Code | Signification |
|---|---|
| 400 | Données invalides (signature, horodatage, validation serializer) |
| 401 | Non authentifié (token absent/expiré) |
| 402 | Solde insuffisant (débit refusé, transaction tracée) |
| 403 | Rôle insuffisant / accès aux données d'autrui |
| 404 | Ressource introuvable (UID, terminal, reçu) |
| 409 | Rejeu détecté (nonce déjà utilisé) |

Le corps d'erreur métier suit la forme `{"detail": "...", "code": "..."}`
(ex : `code = "rejeu_detecte"`, `"solde_insuffisant"`, `"signature_invalide"`).

---

## Authentification — `/api/auth/`

### POST `/api/auth/login/` — public
Requête :
```json
{ "username": "caissier", "password": "caissier1234" }
```
Réponse `200` :
```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "role": "caissier",
  "username": "caissier",
  "user_id": "f0e1…uuid"
}
```

### POST `/api/auth/refresh/` — public
```json
{ "refresh": "<jwt>" }
```
Réponse `200` : `{ "access": "<jwt>" }`.

### POST `/api/auth/logout/` — authentifié
Blacklist le refresh token. Corps : `{ "refresh": "<jwt>" }`. Réponse `205`.

### GET `/api/auth/me/` — authentifié
Profil de l'utilisateur courant (`id`, `username`, `email`, `role`,
`uid_carte` si étudiant lié, …).

---

## Monétique

### POST `/api/transaction/debit/` — caissier/admin + **signature carte**
Débite une carte après vérification de l'enveloppe signée. Requête :
```json
{
  "uid": "SC-2025-00001",
  "terminal_id": "RESTO-01",
  "timestamp": 1718450000000,
  "nonce": "<hex 32 octets>",
  "signature": "<base64 RSA du nonce>",
  "montant": 15000
}
```
- `201` : débit validé (renvoie la transaction).
- `402` : solde insuffisant (transaction `refuse` renvoyée).
- `409` : nonce rejoué. `400` : signature/horodatage invalide. `403` : carte inactive.

> En dev, générer un corps valide :
> `python manage.py simuler_scan --uid SC-2025-00001 --terminal RESTO-01 --type debit`
> (puis ajouter `"montant"`). Valable **30 s**.

### POST `/api/transaction/credit/` — caissier/admin
Recharge au guichet (pas de signature). Requête :
```json
{ "uid": "SC-2025-00001", "montant": 50000, "terminal_id": "RECH-01" }
```
Réponse `201` : la transaction de crédit.

### GET `/api/solde/<uid>/` — étudiant (le sien) / admin
Réponse `200` :
```json
{ "uid": "SC-2025-00001", "montant": 1235000, "montant_fcfa": 12350, "version": 3, "mis_a_jour": "…" }
```

### GET `/api/transactions/<uid>/` — étudiant (le sien) / admin
Liste **paginée**. Filtres : `?type=`, `?statut=`, `?date_debut=AAAA-MM-JJ`,
`?date_fin=AAAA-MM-JJ`, `?page=`, `?page_size=`. Réponse paginée
`{ "count", "next", "previous", "results": [ … ] }`.

### POST `/api/carte/bloquer/` — admin
`{ "uid": "SC-2025-00001" }` → `200 { "uid", "statut": "bloque", "detail" }`.

### GET `/api/stats/dashboard/` — admin
KPIs globaux :
```json
{
  "etudiants_total": 30, "cartes_actives": 28, "cartes_bloquees": 1,
  "transactions_total": 164, "transactions_aujourdhui": 12,
  "repartition_statut": { "valide": 160, "refuse": 4 },
  "volume_debit_centimes": 6535000, "volume_credit_centimes": 30000000,
  "solde_total_centimes": 23465000
}
```

---

## Scolarité — `/api/scolarite/`

### POST `/api/scolarite/payer/` — caissier
```json
{ "uid": "SC-2025-00001", "type_periode": "mensuel", "periode_couverte": "2026-06", "montant": 5000000 }
```
`type_periode` ∈ `mensuel` (`periode_couverte` = `AAAA-MM`) | `semestriel`
(`AAAA-S1`/`AAAA-S2`). Réponse `201` : le paiement (avec `numero_recu`).

### GET `/api/scolarite/statut/<uid>/` — contrôleur/admin
**Contrat figé** (aucune donnée nominative/financière) :
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
`statut` ∈ `a_jour` | `en_retard` | `exonere`.

### GET `/api/scolarite/recu/<id>/` — étudiant (le sien) / admin
Renvoie un **PDF** (`application/pdf`, `Content-Disposition: attachment`).
`<id>` = UUID du paiement.

### POST `/api/scolarite/exonerer/` — admin
```json
{ "uid": "SC-2025-00001", "periode_couverte": "2026-S1", "montant": 0 }
```
Réponse `201` : le paiement d'exonération créé.

---

## IoT — `/api/iot/`

### POST `/api/iot/scan/` — **signature carte** (pas de JWT)
Équivalent HTTP du flux MQTT. Requête :
```json
{
  "uid": "SC-2025-00001",
  "terminal_id": "RESTO-01",
  "timestamp": 1718450000000,
  "nonce": "<hex>",
  "signature": "<base64>",
  "type": "identification"
}
```
Réponse `200` :
```json
{
  "accepte": true, "uid": "SC-2025-00001", "filiere": "DIC1 — L3 Informatique",
  "statut_carte": "actif", "terminal": "RESTO-01",
  "type_scan": "identification", "scan_id": "…uuid"
}
```
Mêmes refus que le débit (400/403/409).

---

## Référentiels

### `/api/etudiants/` — lecture caissier/admin, écriture admin
CRUD complet (`GET` liste/détail, `POST`, `PUT/PATCH`, `DELETE`).
Clé d'accès au détail : l'**UID de carte** (`/api/etudiants/SC-2025-00001/`).
En écriture, `nom`/`prenom`/`matricule` sont fournis en clair et **chiffrés**
automatiquement au stockage.

### `/api/terminaux/` — lecture authentifié, écriture admin
CRUD complet. Clé d'accès au détail : le **code** (`/api/terminaux/RESTO-01/`).

---

## Divers
- `GET /api/sante/` — healthcheck public (`{ "statut": "ok", … }`).
- `/admin/` — interface d'administration Django.
