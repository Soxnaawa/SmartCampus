import { useState } from "react";
import { getTransactions } from "../api";

export default function Transactions() {
  const [uid, setUid] = useState("");
  const [liste, setListe] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cherche, setCherche] = useState(false);

  const charger = async (e) => {
    e.preventDefault();
    if (!uid.trim()) return;
    setLoading(true);
    setError("");
    setCherche(true);
    try {
      const res = await getTransactions(uid.trim());
      setListe(res.data.results || res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Impossible de charger l'historique."
      );
      setListe([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Historique transactions</h2>

      <form className="search-row" onSubmit={charger}>
        <input
          type="text"
          value={uid}
          onChange={(e) => setUid(e.target.value)}
          placeholder="SC-2025-00001"
        />
        <button type="submit">Charger</button>
      </form>

      {loading && <p className="muted">Chargement...</p>}
      {error && <p className="error-text">{error}</p>}

      <div className="list-stack">
        {liste.map((t) => {
          const debit = t.type === "debit";
          return (
            <div className="list-row" key={t.id}>
              <div className="row-with-icon">
                <div
                  className={
                    debit ? "icon-box icon-box-coral" : "icon-box icon-box-teal"
                  }
                >
                  <i className={debit ? "ti ti-arrow-down" : "ti ti-arrow-up"}></i>
                </div>
                <div>
                  <p className="row-title">{t.type_libelle}</p>
                  <p className="row-subtitle">{t.statut_libelle}</p>
                </div>
              </div>
              <span className={debit ? "amount-debit" : "amount-credit"}>
                {debit ? "-" : "+"}
                {t.montant} FCFA
              </span>
            </div>
          );
        })}
        {cherche && !loading && liste.length === 0 && (
          <p className="muted">Aucune transaction pour cet UID.</p>
        )}
      </div>
    </div>
  );
}
