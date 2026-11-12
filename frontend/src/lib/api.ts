import axios, { AxiosError } from "axios";

const API = import.meta.env.VITE_API_BASE || "/api";

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aether_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("aether_token");
      if (typeof window !== "undefined") window.location.pathname = "/login";
    }
    return Promise.reject(error);
  },
);

export type User = { id: number; username: string; is_admin: boolean };
