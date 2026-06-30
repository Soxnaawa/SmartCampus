import axios from "axios";

// URL du backend P3 -- changer si ngrok est relance
const API_BASE = "https://subcerebellar-chalcographic-sawyer.ngrok-free.dev";

const api = axios.create({
  baseURL: API_BASE,
});

// Ajoute automatiquement le token JWT a chaque requete si present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("smartcampus_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = (username, password) =>
  api.post("/api/auth/login/", { username, password });

export const getDashboard = () => api.get("/api/stats/dashboard/");

export const getEtudiants = () => api.get("/api/etudiants/");

export const getEtudiant = (uid) => api.get(`/api/etudiants/${uid}/`);

export const getTransactions = (uid, params) =>
  api.get(`/api/transactions/${uid}/`, { params });

export const getSolde = (uid) => api.get(`/api/solde/${uid}/`);

export const crediter = (uid, montant) =>
  api.post("/api/transaction/credit/", { uid, montant });

export const bloquerCarte = (uid) =>
  api.post("/api/carte/bloquer/", { uid });

export default api;
