import { extractErrorMessage } from "./apiError.ts";
import type { AuthUser, Role } from "./types.ts";

const STORAGE_KEY = "educa_auth";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export interface Session {
  token: string;
  user: AuthUser;
}

interface TokenResponse {
  access_token: string;
  user: AuthUser;
}

async function post(path: string, body: unknown): Promise<Session> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(extractErrorMessage(data, res.statusText));
  }
  const token = data as TokenResponse;
  const session: Session = { token: token.access_token, user: token.user };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  return session;
}

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}

export function logOut() {
  localStorage.removeItem(STORAGE_KEY);
}

export function logIn(email: string, password: string): Promise<Session> {
  return post("/auth/login", { email, password });
}

export function signUp(email: string, password: string, name: string, role: Role): Promise<Session> {
  return post("/auth/signup", { email, password, name, role });
}
