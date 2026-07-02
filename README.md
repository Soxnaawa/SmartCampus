# Module IA — Smart Campus
## README : Comment exécuter le code

---

## Ce que fait ce code en résumé

Ce script Python est le **cerveau analytique** du projet Smart Campus.
Il se connecte aux données de P3 (ou utilise des données simulées)
et fait tourner 3 algorithmes d'intelligence artificielle :

| Mission | Algorithme | Ce qu'il produit |
|---|---|---|
| Détecter les fraudes | Isolation Forest + Random Forest | Liste d'alertes |
| Comprendre les habitudes | K-Means | Profils étudiants |
| Prévoir l'affluence | Régression linéaire | Courbe par heure |

---

## Prérequis

Python 3.8 ou plus installé sur ton PC.
Vérifier avec :
```bash
python --version
```

---

## Installation (une seule fois)

```bash
pip install pandas numpy scikit-learn matplotlib requests
```

---

## Les 3 modes d'exécution

### MODE 1 — Avec l'URL de P3 (ngrok ou même WiFi)

**Étape 1** : Ouvre le fichier `smart_campus_ia_p3_v2.py`

**Étape 2** : Modifie les 3 premières lignes de la section CONFIG :

```python
BASE_URL = "https://abc123.ngrok.io"   # ← URL que P3 te donne
USERNAME = "admin"                      # ← ne pas changer
PASSWORD = "admin1234"                  # ← ne pas changer
```

**Étape 3** : Lance le script :
```bash
python smart_campus_ia_p3_v2.py
```

Ce que tu verras dans le terminal :
```
[1] Connexion à l'API P3...
    Connexion réussie.
[2] Récupération des étudiants...
    30 étudiants trouvés : ['SC-2025-00001', ...]
[3] Récupération des transactions...
    245 transactions récupérées depuis P3.
...
```

---

### MODE 2 — Avec le fichier JSON de P3

Si P3 t'a envoyé un fichier `transactions_export.json` sur WhatsApp ou GitHub :

**Étape 1** : Mets le fichier JSON dans le même dossier que le script.

**Étape 2** : Crée un nouveau fichier `charger_json.py` avec ce contenu :

```python
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report, f1_score,
                             precision_score, recall_score,
                             mean_absolute_error, r2_score,
                             silhouette_score)
from sklearn.preprocessing import LabelEncoder, StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ── CHARGEMENT DU FICHIER JSON DE P3 ─────────────────────────
print("Chargement du fichier JSON de P3...")

with open("transactions_export.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"  {len(data)} transactions chargées.")

# ── CONSTRUCTION DU DATAFRAME ─────────────────────────────────
rows = []
for tx in data:
    # Montant : centimes → FCFA
    montant_fcfa    = int(tx.get("montant", 0)) / 100
    solde_avant_fcfa = int(tx.get("solde_avant", 500000)) / 100

    # Heure depuis date_heure
    date_heure = tx.get("date_heure") or tx.get("created_at") or ""
    try:
        dt           = pd.to_datetime(date_heure)
        heure        = dt.hour
        date_str     = dt.strftime("%Y-%m-%d")
        jour_semaine = dt.weekday()
    except Exception:
        heure, date_str, jour_semaine = 12, "2025-01-01", 0

    # Terminal → service
    terminal = str(tx.get("terminal_id", "INCONNU"))
    if   "RESTO"  in terminal.upper(): service = "restaurant"
    elif "BIBLIO" in terminal.upper(): service = "bibliotheque"
    elif "PHOTO"  in terminal.upper(): service = "photocopie"
    elif "TRANS"  in terminal.upper(): service = "transport"
    elif "SPORT"  in terminal.upper(): service = "sport"
    else:                              service = "autre"

    # Statut → label fraude
    statut   = str(tx.get("statut", "valide")).lower()
    is_fraud = 1 if statut in ["suspect","fraude","bloque","refuse"] else 0

    rows.append({
        "etudiant_id":  tx.get("uid") or tx.get("etudiant_id","INCONNU"),
        "service":      service,
        "terminal_id":  terminal,
        "montant":      montant_fcfa,
        "heure":        heure,
        "date":         date_str,
        "jour_semaine": jour_semaine,
        "solde_avant":  solde_avant_fcfa,
        "statut":       statut,
        "is_fraud":     is_fraud,
    })

df = pd.DataFrame(rows)
df["nb_transactions_jour"] = df.groupby(
    ["etudiant_id","date"])["montant"].transform("count")

print(f"  Dataset : {len(df)} transactions")
print(f"  Étudiants : {df['etudiant_id'].nunique()}")
print(f"  Suspects  : {df['is_fraud'].sum()}")
print(f"  Montants  : {df['montant'].min():.0f} → {df['montant'].max():.0f} FCFA")
print(df[["etudiant_id","service","montant","heure","is_fraud"]].head(5).to_string(index=False))

# ── FEATURE ENGINEERING ───────────────────────────────────────
le_svc = LabelEncoder()
le_ter = LabelEncoder()
df["service_enc"]         = le_svc.fit_transform(df["service"])
df["terminal_enc"]        = le_ter.fit_transform(df["terminal_id"])
df["ratio_montant_solde"] = (df["montant"] / df["solde_avant"].replace(0,1)).round(4)
df["heure_sin"]           = np.sin(2*np.pi*df["heure"]/24)
df["heure_cos"]           = np.cos(2*np.pi*df["heure"]/24)

FEATURES = ["montant","heure","nb_transactions_jour",
            "ratio_montant_solde","service_enc","heure_sin","heure_cos"]

# ── ISOLATION FOREST ──────────────────────────────────────────
print("\nIsolation Forest...")
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(df[FEATURES].values)

iso = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
df["iso_pred"]  = iso.fit_predict(X_scaled)
df["iso_score"] = iso.score_samples(X_scaled)
df["iso_fraud"] = (df["iso_pred"] == -1).astype(int)

if df["is_fraud"].sum() > 0:
    p = precision_score(df["is_fraud"], df["iso_fraud"], zero_division=0)
    r = recall_score   (df["is_fraud"], df["iso_fraud"], zero_division=0)
    f = f1_score       (df["is_fraud"], df["iso_fraud"], zero_division=0)
    print(f"  Précision:{p:.2f}  Rappel:{r:.2f}  F1:{f:.2f}")

print(f"  Alertes détectées : {df['iso_fraud'].sum()}")
print(df[df["iso_fraud"]==1][["etudiant_id","montant","heure","terminal_id"]].head(10).to_string(index=False))

# ── RANDOM FOREST ─────────────────────────────────────────────
print("\nRandom Forest...")
if df["is_fraud"].sum() >= 5:
    X, y = df[FEATURES], df["is_fraud"]
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
    rf = RandomForestClassifier(n_estimators=100,class_weight="balanced",random_state=42)
    rf.fit(Xtr, ytr)
    print(classification_report(yte, rf.predict(Xte), target_names=["Normal","Fraude"]))
else:
    print("  Pas assez de fraudes labellisées.")

# ── K-MEANS ───────────────────────────────────────────────────
print("\nK-Means...")
df_st = (df[df["is_fraud"]==0].groupby("etudiant_id").agg(
    montant_moyen    =("montant","mean"),
    heure_moyenne    =("heure","mean"),
    nb_transactions  =("montant","count"),
    service_principal=("service_enc", lambda x: x.mode()[0])
).reset_index())

if len(df_st) >= 4:
    X_km = StandardScaler().fit_transform(
        df_st[["montant_moyen","heure_moyenne","nb_transactions","service_principal"]].values)
    best_k, best_sil = 2, -1
    for k in range(2, min(7, len(df_st))):
        lbl = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_km)
        s   = silhouette_score(X_km, lbl)
        if s > best_sil: best_k, best_sil = k, s
    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    df_st["cluster"] = km.fit_predict(X_km)
    print(f"  K={best_k}  silhouette={best_sil:.3f}")
    print(df_st.groupby("cluster").agg(
        nb=("etudiant_id","count"),
        montant=("montant_moyen","mean"),
        heure=("heure_moyenne","mean")).to_string())
else:
    best_k = 0
    print("  Pas assez d'étudiants.")

# ── RÉGRESSION AFFLUENCE ──────────────────────────────────────
print("\nPrédiction d'affluence...")
aff = (df.groupby("heure").size().reindex(range(24),fill_value=0)
         .reset_index(name="affluence"))
aff["heure_sin"] = np.sin(2*np.pi*aff["heure"]/24)
aff["heure_cos"] = np.cos(2*np.pi*aff["heure"]/24)
reg = LinearRegression()
reg.fit(aff[["heure","heure_sin","heure_cos"]], aff["affluence"])
pred = reg.predict(aff[["heure","heure_sin","heure_cos"]]).clip(0)
print(f"  MAE:{mean_absolute_error(aff['affluence'],pred):.1f}  R²:{r2_score(aff['affluence'],pred):.3f}")

# ── GRAPHIQUES ────────────────────────────────────────────────
print("\nGénération des graphiques...")
fig, axes = plt.subplots(2,2,figsize=(14,10))
fig.suptitle(f"Smart Campus — Module IA | {len(df)} transactions (données P3)",
             fontsize=13, fontweight="bold")

axes[0,0].hist(df[df["is_fraud"]==0]["iso_score"],bins=30,alpha=0.7,
               color="#378ADD",label="Normal")
if df["is_fraud"].sum()>0:
    axes[0,0].hist(df[df["is_fraud"]==1]["iso_score"],bins=10,alpha=0.8,
                   color="#E24B4A",label="Fraude")
axes[0,0].set_title("Isolation Forest — Scores"); axes[0,0].legend(); axes[0,0].grid(alpha=0.3)

axes[0,1].scatter(df[df["iso_fraud"]==0]["heure"],df[df["iso_fraud"]==0]["montant"],
                  alpha=0.3,s=15,color="#378ADD",label="Normal")
axes[0,1].scatter(df[df["iso_fraud"]==1]["heure"],df[df["iso_fraud"]==1]["montant"],
                  alpha=0.8,s=50,color="#E24B4A",label="Alerte")
axes[0,1].set_title("Heure vs Montant (FCFA)"); axes[0,1].legend(); axes[0,1].grid(alpha=0.3)

if best_k>=2 and "cluster" in df_st.columns:
    colors=["#378ADD","#E24B4A","#27a065","#EF9F27","#7F77DD"]
    for c in range(best_k):
        m=df_st["cluster"]==c
        axes[1,0].scatter(df_st[m]["heure_moyenne"],df_st[m]["montant_moyen"],
                          c=colors[c],label=f"Profil {c+1}",alpha=0.7,s=60)
    axes[1,0].set_title(f"K-Means — {best_k} profils"); axes[1,0].legend(); axes[1,0].grid(alpha=0.3)

axes[1,1].bar(range(24),aff["affluence"],color="#AAAAAA",alpha=0.5,label="Réel")
axes[1,1].plot(range(24),pred,color="#E24B4A",lw=2,marker="o",ms=4,label="Prédiction")
axes[1,1].set_title("Affluence prédite"); axes[1,1].legend(); axes[1,1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("smart_campus_resultats_json.png", dpi=150, bbox_inches="tight")

df.to_csv("transactions_p3.csv", index=False)
df[df["iso_fraud"]==1].to_csv("alertes_fraude.csv", index=False)

print("\nFichiers générés :")
print("  smart_campus_resultats_json.png")
print("  transactions_p3.csv")
print("  alertes_fraude.csv")
```

**Étape 3** : Lance ce fichier :
```bash
python charger_json.py
```

---

### MODE 3 — Sans P3 (données simulées)

Si P3 n'est pas disponible, utilise directement :
```bash
python smart_campus_ia_p3_v2.py
```
Le code détecte automatiquement que P3 est inaccessible
et bascule sur les données simulées. Tu vois ce message :
```
→ P3 indisponible — données simulées (mode développement).
```

---

## Structure des fichiers

```
smartCampusIA/
│
├── smart_campus_ia_p3_v2.py     ← script principal (URL ou simulé)
├── charger_json.py               ← script pour fichier JSON de P3
├── transactions_export.json      ← fichier JSON de P3 (si disponible)
│
└── outputs/
    ├── transactions_p3.csv           ← toutes les transactions traitées
    ├── alertes_fraude.csv            ← transactions suspectes uniquement
    └── smart_campus_resultats.png    ← les 4 graphiques
```

---

## Ce que produit le code

### 1. Dans le terminal
```
[1] Connexion...        → statut de connexion à P3
[2] Étudiants...        → nombre d'étudiants récupérés
[3] Transactions...     → nombre de transactions chargées
[4] Dataset...          → résumé des données
[5] Features...         → variables calculées
[6] Isolation Forest... → F1, précision, rappel + top alertes
[7] Random Forest...    → rapport de classification complet
[8] K-Means...          → K optimal + description des profils
[9] Affluence...        → MAE, R² + prédiction heure par heure
[10] Graphiques...      → fichier PNG généré
```

### 2. Fichiers générés
| Fichier | Contenu |
|---|---|
| `transactions_p3.csv` | Toutes les transactions avec scores d'anomalie |
| `alertes_fraude.csv` | Uniquement les transactions suspectes |
| `smart_campus_resultats.png` | 4 graphiques côte à côte |

---

## Erreurs fréquentes et solutions

| Erreur | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'pandas'` | Bibliothèques pas installées | `pip install pandas numpy scikit-learn matplotlib requests` |
| `ConnectionError` | Serveur P3 éteint | Normal — le code bascule sur les données simulées |
| `JSONDecodeError` | Fichier JSON mal formé | Vérifier que le fichier est complet et bien encodé UTF-8 |
| `KeyError: 'uid'` | Champs différents dans le JSON | Vérifier les noms de champs avec P3 |
| Graphiques pas générés | Dossier en lecture seule | Lancer le script depuis ton Bureau ou dossier Documents |

---

## Résultats attendus

| Modèle | Métrique | Données simulées | Données réelles (objectif) |
|---|---|---|---|
| Isolation Forest | F1-score | 0.97 | 0.75 — 0.85 |
| Random Forest | F1-score | 1.00 | 0.85 — 0.92 |
| K-Means | Silhouette | 0.36 | 0.40 — 0.55 |
| Régression | R² | 0.56 | 0.60 — 0.75 |

Les résultats sur données simulées sont meilleurs que sur données réelles
car les données simulées sont "propres" et bien séparées.
Les données réelles auront plus de bruit et de cas ambigus.
