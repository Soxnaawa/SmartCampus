import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">
            <i className="ti ti-credit-card"></i>
          </div>
          <span>Smart Campus</span>
        </div>

        <nav>
          <NavLink to="/dashboard" className="nav-btn">
            <i className="ti ti-chart-bar"></i>
            Dashboard
          </NavLink>
          <NavLink to="/etudiants" className="nav-btn">
            <i className="ti ti-users"></i>
            Etudiants
          </NavLink>
          <NavLink to="/transactions" className="nav-btn">
            <i className="ti ti-receipt"></i>
            Transactions
          </NavLink>
          <NavLink to="/scan" className="nav-btn">
            <i className="ti ti-scan"></i>
            Simuler un scan
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="conn-status">
            <span className="status-dot"></span>
            {user?.username}
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <i className="ti ti-logout"></i>
            Deconnexion
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
