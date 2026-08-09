import axios from "axios";
import { useAuthStore } from "./auth-store";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

console.log("VITE_API_URL =", API_URL);

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;

  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }

  return config;
});