# SmartCampus — Modèle de Menaces (M3 Cybersécurité)

**Auteur :** P4 — Cybersécurité  
**Méthode :** STRIDE + DREAD  
**Date :** Semaine 1 — Juin 2026  

---

## 1. Périmètre de l'analyse

Le système SmartCampus couvre :

| Composant | Description |
|-----------|-------------|
| Carte RFID/NFC étudiant | Identité + portefeuille, données chiffrées AES-256 |
| Terminal de lecture | RC522 simulé, publie sur MQTT |
| Broker MQTT | Mosquitto, communication terminal ↔ backend |
| Backend Django REST | API paiement, scolarité, authentification JWT |
| Service IA | Flask, scoring de fraude |
| Base de données | PostgreSQL (transactions), Redis (sessions) |
| Frontend React | Dashboard admin + app étudiant |

---

## 2. Acteurs & niveaux de confiance

| Acteur | Niveau de confiance | Accès |
|--------|--------------------|----|
| Étudiant authentifié | Faible | Lecture solde, historique propre |
| Caissier | Moyen | Débits, consultation |
| Contrôleur | Moyen | Vérification scolarité uniquement |
| Admin | Élevé | Toutes opérations, gestion cartes |
| Attaquant externe | Zéro | Aucun accès légitime |
| Attaquant interne | Faible–Moyen | Accès physique campus |

---

## 3. Surfaces d'attaque

```
[Carte NFC] ──NFC──► [Terminal RC522] ──MQTT──► [Broker Mosquitto]
                                                         │
                                              ┌──────────▼──────────┐
                                              │   Backend Django    │
                                              │   API REST (JWT)    │
                                              └──┬──────────────┬───┘
                                                 │              │
                                          [PostgreSQL]      [Service IA]
                                          [Redis]
                                                 │
                                         [Frontend React]
                                         [Admin / Étudiant]
```

**Points d'entrée :**
1. Interface NFC (physique, < 10 cm)
2. Canal MQTT (réseau WiFi campus)
3. API REST HTTPS (Internet / réseau interne)
4. Interface Admin web

---

## 4. Menaces STRIDE

### 4.1 Spoofing (Usurpation d'identité)

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-01 | Clonage de carte RFID (copie UID) | Carte NFC | Critique | Auth mutuelle PKI/X.509 — l'UID seul ne suffit pas |
| T-02 | Forgeage de token JWT | Backend API | Élevé | Clé secrète forte (256 bits), rotation mensuelle |
| T-03 | Usurpation de terminal MQTT | Broker | Élevé | Certificats TLS client sur les terminaux |

### 4.2 Tampering (Falsification)

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-04 | Modification du solde en base | PostgreSQL | Critique | Integrity hash sur chaque ligne, audit log immuable |
| T-05 | Altération du payload MQTT en transit | MQTT | Élevé | MQTT over TLS (port 8883) + HMAC payload |
| T-06 | Injection SQL dans l'API | Backend | Critique | ORM Django — requêtes paramétrées obligatoires |

### 4.3 Repudiation (Non-répudiation)

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-07 | Étudiant nie une transaction | Backend | Moyen | Signature RSA de chaque transaction par la carte |
| T-08 | Admin nie une modification | Backend | Moyen | Audit log signé, horodaté, non modifiable |

### 4.4 Information Disclosure (Fuite d'info)

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-09 | Sniffing NFC (< 10 cm) | Carte NFC | Élevé | AES-256-GCM sur toutes les données carte |
| T-10 | Sniffing MQTT WiFi | Broker | Critique | TLS 1.3 obligatoire |
| T-11 | Dump base de données | PostgreSQL | Critique | Chiffrement at-rest (pg_crypto), colonnes sensibles |
| T-12 | Exposition de clés dans le code | Backend | Critique | Variables d'environnement + secrets manager |

### 4.5 Denial of Service

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-13 | Flood de scans MQTT | Broker | Moyen | Rate limiting côté broker (max_connections) |
| T-14 | Brute force API | Backend | Moyen | Throttling Django (django-ratelimit), fail2ban |
| T-15 | Saturation PostgreSQL | BDD | Élevé | Connection pooling (pgBouncer), requêtes optimisées |

### 4.6 Elevation of Privilege

| ID | Menace | Composant | Impact | Contre-mesure |
|----|--------|-----------|--------|---------------|
| T-16 | Élévation de rôle JWT | Backend | Critique | Validation stricte du claim `role`, permissions DRF |
| T-17 | Accès admin via IDOR | Backend | Élevé | Vérifier `request.user.uid == resource.uid` systématiquement |

---

## 5. Scoring DREAD

| ID | Menace | Damage | Repro | Exploit | Affected | Discov | **Score/10** |
|----|--------|--------|-------|---------|----------|--------|-------------|
| T-01 | Clonage carte | 10 | 7 | 6 | 9 | 8 | **8.0** |
| T-06 | SQL Injection | 10 | 9 | 8 | 10 | 7 | **8.8** |
| T-10 | Sniffing MQTT | 9 | 8 | 7 | 8 | 6 | **7.6** |
| T-16 | Élévation JWT | 10 | 8 | 7 | 10 | 5 | **8.0** |
| T-05 | Falsification MQTT | 9 | 7 | 6 | 8 | 5 | **7.0** |

**Priorité de traitement :** T-06 > T-01 = T-16 > T-10 > T-05

---

## 6. Mesures de sécurité implémentées (P4)

| Mesure | Fichier | Statut |
|--------|---------|--------|
| PKI hiérarchique (Root CA + cartes) | `pki/setup_pki.py` | ✅ Implémenté |
| AES-256-GCM données carte | `crypto/aes_gcm.py` | ✅ Implémenté |
| Anti-replay (nonce + timestamp + HMAC) | `attacks/replay/replay_demo.py` | ✅ Démonstration |
| Audit statique du code | `audit/security_audit.py` | ✅ Implémenté |
| Tests d'intégration sécurité | `tests/test_security.py` | ✅ Implémenté |

---

## 7. Checklist de revue (Semaine 4 — Audit P3/P5)

```
[ ] Toutes les requêtes SQL utilisent l'ORM Django (pas de f-string SQL)
[ ] JWT : algorithm=['HS256'], vérification de l'expiration active
[ ] CORS : CORS_ALLOWED_ORIGINS liste blanche (pas de wildcard *)
[ ] Secrets : aucun hardcodé — variables d'environnement uniquement
[ ] HTTPS : TLS 1.2 minimum sur tous les endpoints publics
[ ] MQTT : TLS port 8883, auth par certificat terminal
[ ] Logs : aucun token/password/signature dans les logs applicatifs
[ ] IDOR : chaque endpoint vérifie que l'utilisateur accède à ses propres données
[ ] Rate limiting : actif sur /api/v1/auth/ et /api/v1/transaction/
[ ] Dépendances : pip-audit / npm audit sans CVE critique
```
