import { useEffect, useState } from "react";
import { getDashboard } from "../api";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const charger = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getDashboard();
      setStats(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Impossible de charger le dashboard."
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
        <h2>Tableau de bord</h2>
        <button onClick={charger}>
          <i className="ti ti-refresh"></i>
          Actualiser
        </button>
      </div>

      {loading && <p className="muted">Chargement...</p>}
      {error && <p className="error-text">{error}</p>}

      {stats && (
        <div className="kpi-grid">
          <div className="kpi-card" style={{ borderLeftColor: "#378ADD" }}>
            <p className="kpi-label">
              <i className="ti ti-users"></i> Etudiants
            </p>
            <p className="kpi-value">{stats.etudiants_total}</p>
          </div>

          <div className="kpi-card" style={{ borderLeftColor: "#1D9E75" }}>
            <p className="kpi-label">
              <i className="ti ti-circle-check"></i> Cartes actives
            </p>
            <p className="kpi-value kpi-success">{stats.cartes_actives}</p>
          </div>

          <div className="kpi-card" style={{ borderLeftColor: "#E24B4A" }}>
            <p className="kpi-label">
              <i className="ti ti-lock"></i> Cartes bloquees
            </p>
            <p className="kpi-value kpi-danger">{stats.cartes_bloquees}</p>
          </div>

          <div className="kpi-card" style={{ borderLeftColor: "#7F77DD" }}>
            <p className="kpi-label">
              <i className="ti ti-receipt"></i> Transactions
            </p>
            <p className="kpi-value">{stats.transactions_total}</p>
          </div>

          <div className="kpi-card" style={{ borderLeftColor: "#BA7517" }}>
            <p className="kpi-label">
              <i className="ti ti-calendar"></i> Aujourd'hui
            </p>
            <p className="kpi-value kpi-warning">
              {stats.transactions_aujourdhui}
            </p>
          </div>

          <div
            className="kpi-card kpi-wide"
            style={{ borderLeftColor: "#1D9E75" }}
          >
            <p className="kpi-label">
              <i className="ti ti-wallet"></i> Solde total cumule
            </p>
            <p className="kpi-value kpi-success">
              {Math.round((stats.solde_total_centimes || 0) / 100).toLocaleString()}{" "}
              FCFA
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
