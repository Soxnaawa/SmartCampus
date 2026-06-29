# SmartCampus — Branche `feature/p4-securite`

**Responsable :** P4 — Cybersécurité  
**Module :** M3 — Cybersécurité & Cryptographie

---

## Structure

```
feature_p4_securite/
├── pki/
│   ├── setup_pki.py          # Génère Root CA + 20 certificats cartes
│   ├── root-ca/              # Root CA (clé privée + certificat)
│   ├── cards/                # Clés et certificats par carte (SC-2025-XXXXX)
│   └── certs/
│       └── card_registry.json  # Registre JSON de toutes les cartes
│
├── crypto/
│   └── aes_gcm.py            # AES-256-GCM : chiffrement carte, signature RSA
│
├── attacks/
│   └── replay/
│       └── replay_demo.py    # Démo replay attack (4 phases) + contre-mesures
│
├── audit/
│   └── security_audit.py     # Audit statique : 12 règles SAST (SQL, JWT, CORS…)
│
├── tests/
│   └── test_security.py      # 18 tests unitaires — 18/18 passent
│
└── docs/
    └── threat_model.md       # Modèle de menaces STRIDE + scoring DREAD
```

---

## Lancer les tests

```bash
cd feature_p4_securite
python3 tests/test_security.py
```

## Initialiser la PKI

```bash
cd feature_p4_securite/pki
python3 setup_pki.py          # génère Root CA + 20 cartes
python3 setup_pki.py --cards 5  # générer seulement 5 cartes
```

## Démontrer l'attaque replay

```bash
python3 feature_p4_securite/attacks/replay/replay_demo.py
```

## Auditer le code d'un module

```bash
# Auditer le backend (P3)
python3 feature_p4_securite/audit/security_audit.py ../feature/p3-backend \
        --json-out audit_p3.json --md-out audit_p3.md

# Auditer tout le projet
python3 feature_p4_securite/audit/security_audit.py .. \
        --json-out audit_full.json --md-out audit_full.md
```

---

## Livrables par semaine

| Semaine | Livrable | Statut |
|---------|----------|--------|
| S1 | Modèle de menaces + PKI initialisée | ✅ |
| S2 | AES-256-GCM données carte | ✅ |
| S3 | Démo replay attack + contre-mesure nonce | ✅ |
| S4 | Audit sécurité modules P2/P3/P5 | ✅ (prêt à lancer) |
| S5 | Section sécurité rapport final + preuves | 🔄 |

---

## Dépendances

```bash
pip install cryptography --break-system-packages
```

Aucune autre dépendance externe — stdlib Python uniquement pour le reste.
