import axios from "axios";
import { useAuthStore } from "./auth-store";

const configuredApiUrl = import.meta.env.VITE_API_URL || "https://data-dojo-api.onrender.com";

// VITE_API_URL is the server origin (without a trailing /api). Accept the old
// value ending in /api as well so existing deployments do not generate /api/api.
export const API_ORIGIN = configuredApiUrl.replace(/\/+$/, "").replace(/\/api$/, "");

export function getAuthToken(): string | null {
  const stateToken = useAuthStore.getState().token;
  if (stateToken) return stateToken;
  if (typeof window === "undefined") return null;

  try {
    const persisted = JSON.parse(window.localStorage.getItem("ddj-auth") || "null");
    return persisted?.state?.token || null;
  } catch {
    return null;
  }
}

export const api = axios.create({
  baseURL: API_ORIGIN,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = getAuthToken();

  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }

  return config;
});
