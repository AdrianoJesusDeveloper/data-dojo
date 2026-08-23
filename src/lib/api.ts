import axios from "axios";
import { useAuthStore } from "./auth-store";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://data-dojo.onrender.com";

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
