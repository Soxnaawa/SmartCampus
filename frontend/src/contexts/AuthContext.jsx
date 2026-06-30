import { createContext, useContext, useState } from "react";
import { login as apiLogin } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("smartcampus_user");
    return saved ? JSON.parse(saved) : null;
  });

  const login = async (username, password) => {
    const res = await apiLogin(username, password);
    const { access, refresh, role } = res.data;
    localStorage.setItem("smartcampus_token", access);
    localStorage.setItem("smartcampus_refresh", refresh || "");
    const userData = { username, role };
    localStorage.setItem("smartcampus_user", JSON.stringify(userData));
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("smartcampus_token");
    localStorage.removeItem("smartcampus_refresh");
    localStorage.removeItem("smartcampus_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
