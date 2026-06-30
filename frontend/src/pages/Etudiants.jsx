import { useEffect, useState } from "react";
import { getEtudiants } from "../api";

export default function Etudiants() {
  const [liste, setListe] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const charger = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getEtudiants();
      setListe(res.data.results || res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Impossible de charger les etudiants."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    charger();
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Etudiants</h2>
        <button onClick={charger}>
          <i className="ti ti-refresh"></i>
          Actualiser
        </button>
      </div>

      {loading && <p className="muted">Chargement...</p>}
      {error && <p className="error-text">{error}</p>}

      <div className="list-stack">
        {liste.map((e) => (
          <div className="list-row" key={e.uid_carte}>
            <div>
              <p className="row-title">{e.uid_carte}</p>
              <p className="row-subtitle">{e.filiere}</p>
            </div>
            <span
              className={
                e.statut === "actif" ? "badge badge-success" : "badge badge-danger"
              }
            >
              {e.statut}
            </span>
          </div>
        ))}
        {!loading && liste.length === 0 && (
          <p className="muted">Aucun etudiant trouve.</p>
        )}
      </div>
    </div>
  );
}
