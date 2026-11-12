import { api } from "./api";
import type { User } from "./api";

export async function login(username: string, password: string) {
  const { data } = await api.post<{ ok: boolean; token: string; user: User }>("/auth/login", {
    username,
    password,
  });
  if (data.token) localStorage.setItem("aether_token", data.token);
  return data;
}

export async function logout() {
  try {
    await api.post("/auth/logout");
  } finally {
    localStorage.removeItem("aether_token");
  }
}

export async function me() {
  const { data } = await api.get<{ user: User }>("/auth/me");
  return data.user;
}

export async function csrf() {
  const { data } = await api.get<{ csrf_token: string }>("/auth/csrf");
  return data.csrf_token;
}
