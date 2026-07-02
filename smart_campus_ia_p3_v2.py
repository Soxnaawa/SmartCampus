"""
Smart Campus - Module IA connecté à l'API P3 (v2)
==================================================
Basé sur le README officiel de P3 (ESP/UCAD).

Points importants lus dans le README de P3 :
  - Montants en CENTIMES de FCFA → on divise par 100
  - Clés primaires en UUID
  - Données personnelles chiffrées (AES-256-GCM) → on ne voit que les UID
  - ~30 étudiants générés par seed_data avec historique de transactions
  - Authentification JWT obligatoire (access token 15 min)
  - Pagination sur /api/transactions/<uid>/

CONFIGURATION : modifier uniquement le bloc CONFIG ci-dessous.
"""

import requests
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

# ─────────────────────────────────────────────
# CONFIG — ne modifier que ces lignes
# ─────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000"  # URL serveur P3
                                     # Si ngrok : "https://abc123.ngrok.io"
                                     # Si même WiFi : "http://192.168.X.X:8000"
USERNAME = "admin"
PASSWORD = "admin1234"

print("=" * 60)
print("  SMART CAMPUS — MODULE IA  (connecté à P3 v2)")
print("=" * 60)

# ─────────────────────────────────────────────
# ÉTAPE 1 — AUTHENTIFICATION JWT
# ─────────────────────────────────────────────
print("\n[1] Connexion à l'API P3...")

access_token = None
session = requests.Session()

try:
    resp = session.post(
        f"{BASE_URL}/api/auth/login/",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10
    )
    resp.raise_for_status()
    access_token = resp.json()["access"]
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    print("    Connexion réussie.")

except requests.exceptions.ConnectionError:
    print("    ERREUR : Serveur P3 inaccessible.")
    print("    Solutions possibles :")
    print("      1. P3 lance : python manage.py runserver")
    print("      2. P3 utilise ngrok → mettre l'URL ngrok dans BASE_URL")
    print("      3. Même WiFi → mettre l'IP locale de P3 dans BASE_URL")
    print("    → Bascule automatique sur données simulées.\n")

except Exception as e:
    print(f"    ERREUR login : {e}")

# ─────────────────────────────────────────────
# ÉTAPE 2 — RÉCUPÉRATION DES ÉTUDIANTS
# ─────────────────────────────────────────────
print("[2] Récupération des étudiants...")

uids = []

if access_token:
    try:
        resp = session.get(f"{BASE_URL}/api/etudiants/", timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Gère liste directe ou réponse paginée {"results": [...]}
        etudiants = data if isinstance(data, list) else data.get("results", [])
        uids = [e["uid"] for e in etudiants if "uid" in e]
        print(f"    {len(uids)} étudiants trouvés : {uids[:5]}{'...' if len(uids)>5 else ''}")

    except Exception as e:
        print(f"    ERREUR récupération étudiants : {e}")

# ─────────────────────────────────────────────
# ÉTAPE 3 — RÉCUPÉRATION DES TRANSACTIONS
# ─────────────────────────────────────────────
print("[3] Récupération des transactions...")

all_rows = []

if access_token and uids:
    for uid in uids:
        page = 1
        while True:
            try:
                resp = session.get(
                    f"{BASE_URL}/api/transactions/{uid}/",
                    params={"page": page},
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json()

                # Gère liste directe ou paginée
                if isinstance(data, list):
                    transactions = data
                    has_next = False
                else:
                    transactions = data.get("results", [])
                    has_next = bool(data.get("next"))

                for tx in transactions:
                    # ── Montant : centimes → FCFA (÷ 100) ──
                    montant_centimes = tx.get("montant", 0) or 0
                    montant_fcfa     = int(montant_centimes) / 100

                    solde_avant_centimes = tx.get("solde_avant", 500000) or 500000
                    solde_avant_fcfa     = int(solde_avant_centimes) / 100

                    # ── Heure depuis date_heure ──
                    date_heure = tx.get("date_heure") or tx.get("created_at") or ""
                    try:
                        dt = pd.to_datetime(date_heure)
                        heure        = dt.hour
                        date_str     = dt.strftime("%Y-%m-%d")
                        jour_semaine = dt.weekday()
                    except Exception:
                        heure, date_str, jour_semaine = 12, "2025-01-01", 0

                    # ── Terminal → service ──
                    terminal = str(tx.get("terminal_id", "INCONNU"))
                    # Déduit le service depuis l'ID terminal (ex: RESTO-01 → restaurant)
                    if "RESTO"   in terminal.upper(): service = "restaurant"
                    elif "BIBLIO" in terminal.upper(): service = "bibliotheque"
                    elif "PHOTO"  in terminal.upper(): service = "photocopie"
                    elif "TRANS"  in terminal.upper(): service = "transport"
                    elif "SPORT"  in terminal.upper(): service = "sport"
                    else:                              service = "autre"

                    # ── Statut → label fraude ──
                    statut   = str(tx.get("statut", "valide")).lower()
                    is_fraud = 1 if statut in ["suspect","fraude","bloque","refuse"] else 0

                    all_rows.append({
                        "etudiant_id":   uid,
                        "service":       service,
                        "terminal_id":   terminal,
                        "montant":       montant_fcfa,
                        "heure":         heure,
                        "date":          date_str,
                        "jour_semaine":  jour_semaine,
                        "solde_avant":   solde_avant_fcfa,
                        "statut":        statut,
                        "is_fraud":      is_fraud,
                    })

                if not has_next:
                    break
                page += 1

            except Exception as e:
                print(f"    Erreur uid={uid} page={page} : {e}")
                break

    print(f"    {len(all_rows)} transactions récupérées depuis P3.")

# ─────────────────────────────────────────────
# FALLBACK — données simulées si P3 indisponible
# ─────────────────────────────────────────────
if not all_rows:
    print("\n    → P3 indisponible — données simulées (mode développement).")
    np.random.seed(42)
    N, NF = 1000, 50
    SERVICES  = ["restaurant","bibliotheque","photocopie","transport","sport"]
    TERMINAUX = ["RESTO-01","BIBLIO-01","PHOTO-01","TRANS-01","SPORT-01"]
    MONTANTS  = {"restaurant":1500,"bibliotheque":200,"photocopie":500,
                 "transport":300,"sport":1000}

    for _ in range(N):
        svc = np.random.choice(SERVICES, p=[0.50,0.20,0.15,0.10,0.05])
        all_rows.append({
            "etudiant_id":  f"SC-2025-{np.random.randint(1,31):05d}",
            "service":      svc,
            "terminal_id":  TERMINAUX[SERVICES.index(svc)],
            "montant":      max(100, np.random.normal(MONTANTS[svc], MONTANTS[svc]*0.2)),
            "heure":        np.random.choice(list(range(11,15))+list(range(18,21)))
                            if svc=="restaurant" else np.random.randint(8,21),
            "date":         "2025-06-01",
            "jour_semaine": np.random.randint(0,5),
            "solde_avant":  np.random.uniform(2000,20000),
            "statut":       "valide",
            "is_fraud":     0,
        })

    for _ in range(NF):
        all_rows.append({
            "etudiant_id":  f"SC-2025-{np.random.randint(1,31):05d}",
            "service":      "autre",
            "terminal_id":  "T-INCONNU",
            "montant":      np.random.uniform(15000,60000),
            "heure":        np.random.choice([0,1,2,3,22,23]),
            "date":         "2025-06-01",
            "jour_semaine": np.random.randint(0,7),
            "solde_avant":  np.random.uniform(100,2000),
            "statut":       "suspect",
            "is_fraud":     1,
        })

# ─────────────────────────────────────────────
# ÉTAPE 4 — DATAFRAME + FEATURES
# ─────────────────────────────────────────────
print("\n[4] Construction du dataset...")

df = pd.DataFrame(all_rows)
df["nb_transactions_jour"] = df.groupby(
    ["etudiant_id","date"])["montant"].transform("count")

print(f"    Total transactions   : {len(df)}")
print(f"    Étudiants uniques    : {df['etudiant_id'].nunique()}")
print(f"    Transactions suspectes : {df['is_fraud'].sum()}")
print(f"    Plage montants (FCFA): {df['montant'].min():.0f} → {df['montant'].max():.0f}")

print("\n[5] Feature engineering...")
le_svc = LabelEncoder()
le_ter = LabelEncoder()
df["service_enc"]         = le_svc.fit_transform(df["service"])
df["terminal_enc"]        = le_ter.fit_transform(df["terminal_id"])
df["ratio_montant_solde"] = (df["montant"] / df["solde_avant"].replace(0,1)).round(4)
df["heure_sin"]           = np.sin(2*np.pi*df["heure"]/24)
df["heure_cos"]           = np.cos(2*np.pi*df["heure"]/24)

FEATURES = ["montant","heure","nb_transactions_jour",
            "ratio_montant_solde","service_enc","heure_sin","heure_cos"]

# ─────────────────────────────────────────────
# ÉTAPE 6 — ISOLATION FOREST
# ─────────────────────────────────────────────
print("\n[6] Isolation Forest...")

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
    print(f"    Précision : {p:.2f}  |  Rappel : {r:.2f}  |  F1 : {f:.2f}")

print(f"    Anomalies détectées : {df['iso_fraud'].sum()}")
print("\n    Top 10 alertes (montant en FCFA) :")
alertes = (df[df["iso_fraud"]==1]
           .sort_values("iso_score")
           [["etudiant_id","montant","heure","terminal_id","statut","iso_score"]]
           .head(10))
print(alertes.to_string(index=False))

# ─────────────────────────────────────────────
# ÉTAPE 7 — RANDOM FOREST
# ─────────────────────────────────────────────
print("\n[7] Random Forest (supervisé)...")

if df["is_fraud"].sum() >= 5:
    X, y = df[FEATURES], df["is_fraud"]
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42)
    rf.fit(Xtr, ytr)
    ypred = rf.predict(Xte)
    print(classification_report(yte, ypred, target_names=["Normal","Fraude"]))

    feat_imp = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("    Importance des features :")
    for feat, imp in feat_imp.items():
        print(f"    {feat:<30} {'█'*int(imp*40)} {imp:.3f}")
else:
    print("    Pas assez de labels fraude — Random Forest ignoré.")
    print("    (Normal si P3 n'a pas encore de transactions 'suspect' en base)")

# ─────────────────────────────────────────────
# ÉTAPE 8 — K-MEANS
# ─────────────────────────────────────────────
print("\n[8] K-Means — profils comportementaux...")

df_students = (df[df["is_fraud"]==0]
               .groupby("etudiant_id")
               .agg(
                   montant_moyen    =("montant","mean"),
                   heure_moyenne    =("heure","mean"),
                   nb_transactions  =("montant","count"),
                   service_principal=("service_enc", lambda x: x.mode()[0])
               ).reset_index())

if len(df_students) >= 4:
    X_km = df_students[["montant_moyen","heure_moyenne",
                         "nb_transactions","service_principal"]].values
    X_km_sc = StandardScaler().fit_transform(X_km)

    best_k, best_sil = 2, -1
    for k in range(2, min(7, len(df_students))):
        lbl = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_km_sc)
        s   = silhouette_score(X_km_sc, lbl)
        if s > best_sil:
            best_k, best_sil = k, s

    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    df_students["cluster"] = km.fit_predict(X_km_sc)

    print(f"    K optimal = {best_k}  (silhouette = {best_sil:.3f})")
    desc = (df_students.groupby("cluster")
            .agg(nb=("etudiant_id","count"),
                 montant=("montant_moyen", lambda x: f"{x.mean():.0f} FCFA"),
                 heure  =("heure_moyenne", lambda x: f"{x.mean():.1f}h"),
                 txn    =("nb_transactions","mean"))
            .reset_index())
    print(desc.to_string(index=False))
else:
    print(f"    Seulement {len(df_students)} étudiant(s) — clustering ignoré.")
    best_k = 0

# ─────────────────────────────────────────────
# ÉTAPE 9 — PRÉDICTION AFFLUENCE
# ─────────────────────────────────────────────
print("\n[9] Prédiction d'affluence...")

aff = (df.groupby("heure").size()
         .reindex(range(24), fill_value=0)
         .reset_index(name="affluence"))
aff["heure_sin"] = np.sin(2*np.pi*aff["heure"]/24)
aff["heure_cos"] = np.cos(2*np.pi*aff["heure"]/24)

reg = LinearRegression()
reg.fit(aff[["heure","heure_sin","heure_cos"]], aff["affluence"])
pred_aff = reg.predict(aff[["heure","heure_sin","heure_cos"]]).clip(0)

mae = mean_absolute_error(aff["affluence"], pred_aff)
r2  = r2_score(aff["affluence"], pred_aff)
print(f"    MAE : {mae:.1f} transactions  |  R² : {r2:.3f}")
print("\n    Prédiction par heure :")
for h, a in zip(range(24), pred_aff):
    print(f"    {h:02d}h : {'█'*int(a/max(pred_aff.max(),1)*30)} ({int(a)})")

# ─────────────────────────────────────────────
# ÉTAPE 10 — GRAPHIQUES
# ─────────────────────────────────────────────
print("\n[10] Génération des graphiques...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(f"Smart Campus — Module IA  |  {len(df)} transactions",
             fontsize=14, fontweight="bold")

# Scores Isolation Forest
ax1 = axes[0,0]
ax1.hist(df[df["is_fraud"]==0]["iso_score"], bins=30, alpha=0.7,
         color="#378ADD", label="Normal")
if df["is_fraud"].sum() > 0:
    ax1.hist(df[df["is_fraud"]==1]["iso_score"], bins=10, alpha=0.8,
             color="#E24B4A", label="Fraude/Suspect")
ax1.axvline(np.percentile(df["iso_score"],5), color="orange",
            linestyle="--", label="Seuil détection")
ax1.set_title("Isolation Forest — Scores d'anomalie")
ax1.set_xlabel("Score"); ax1.set_ylabel("Nb transactions")
ax1.legend(); ax1.grid(alpha=0.3)

# Montant vs heure
ax2 = axes[0,1]
ax2.scatter(df[df["iso_fraud"]==0]["heure"],
            df[df["iso_fraud"]==0]["montant"],
            alpha=0.3, s=15, color="#378ADD", label="Normal")
ax2.scatter(df[df["iso_fraud"]==1]["heure"],
            df[df["iso_fraud"]==1]["montant"],
            alpha=0.8, s=50, color="#E24B4A", label="Alerte")
ax2.set_title("Heure vs Montant (FCFA)")
ax2.set_xlabel("Heure"); ax2.set_ylabel("Montant (FCFA)")
ax2.legend(); ax2.grid(alpha=0.3)

# K-Means
ax3 = axes[1,0]
if best_k >= 2 and "cluster" in df_students.columns:
    colors = ["#378ADD","#E24B4A","#27a065","#EF9F27","#7F77DD"]
    for c in range(best_k):
        m = df_students["cluster"]==c
        ax3.scatter(df_students[m]["heure_moyenne"],
                    df_students[m]["montant_moyen"],
                    c=colors[c], label=f"Profil {c+1}", alpha=0.7, s=60)
    ax3.set_title(f"K-Means — {best_k} profils étudiants")
    ax3.set_xlabel("Heure moyenne"); ax3.set_ylabel("Montant moyen (FCFA)")
    ax3.legend(); ax3.grid(alpha=0.3)
else:
    ax3.text(0.5,0.5,"Données insuffisantes",ha="center",va="center",
             transform=ax3.transAxes, color="gray", fontsize=12)
    ax3.set_title("K-Means — N/A")

# Affluence
ax4 = axes[1,1]
ax4.bar(range(24), aff["affluence"], color="#AAAAAA", alpha=0.5, label="Réel")
ax4.plot(range(24), pred_aff, color="#E24B4A", lw=2,
         marker="o", ms=4, label="Prédiction")
ax4.set_title("Affluence — Réel vs Prédiction")
ax4.set_xlabel("Heure"); ax4.set_ylabel("Nb transactions")
ax4.set_xticks(range(0,24,2)); ax4.legend(); ax4.grid(alpha=0.3)

plt.tight_layout()
# out_png = "/mnt/user-data/outputs/smart_campus_resultats_p3.png"
out_png = "smart_campus_resultats_p3.png"
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"    Graphiques sauvegardés.")

# ─────────────────────────────────────────────
# EXPORT CSV
# ─────────────────────────────────────────────
# df.to_csv("/mnt/user-data/outputs/transactions_p3.csv", index=False)
# (df[df["iso_fraud"]==1]
#  .sort_values("iso_score")
#  .to_csv("/mnt/user-data/outputs/alertes_fraude_p3.csv", index=False))

df.to_csv("transactions_p3.csv", index=False)
(df[df["iso_fraud"]==1]
 .sort_values("iso_score")
 .to_csv("alertes_fraude_p3.csv", index=False))

source = "API P3 réelle" if (access_token and uids) else "Données simulées"
print(f"""
{'='*60}
  RÉSUMÉ FINAL
{'='*60}
  Source              : {source}
  Transactions        : {len(df)}
  Alertes détectées   : {df['iso_fraud'].sum()}
  Profils étudiants   : {best_k if best_k>=2 else 'N/A'}
  MAE affluence       : {mae:.1f} transactions
  R²  affluence       : {r2:.3f}

  Fichiers générés :
    transactions_p3.csv          ← toutes les transactions
    alertes_fraude_p3.csv        ← alertes uniquement
    smart_campus_resultats_p3.png
{'='*60}
""")
