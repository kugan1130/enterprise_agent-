import { AuthResponse, User } from "../types";

// Base API URL configuration (supports local dev and production builds)
export const getApiBaseUrl = (): string => {
  if (typeof window !== "undefined" && (window as unknown as { VITE_API_URL?: string }).VITE_API_URL) {
    return (window as unknown as { VITE_API_URL: string }).VITE_API_URL;
  }
  return typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
};

const TOKEN_KEY = "nexa_token";
const USER_KEY = "nexa_user";

export const getStoredToken = (): string => {
  return localStorage.getItem(TOKEN_KEY) || "";
};

export const getStoredUser = (): User | null => {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
};

export const saveAuthData = (token: string, user: User): void => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearAuthData = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const hasStoredAuth = (): boolean => {
  return Boolean(getStoredToken() && getStoredUser());
};

export const validateSession = async (): Promise<User | null> => {
  const token = getStoredToken();
  const user = getStoredUser();
  if (!token || !user) {
    clearAuthData();
    return null;
  }

  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    clearAuthData();
    return null;
  }

  const profile = (await res.json()) as User;
  saveAuthData(token, profile);
  return profile;
};

export const authService = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const baseUrl = getApiBaseUrl();
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.error?.message || data.detail || "Unable to sign in. Please check your credentials.";
      throw new Error(msg);
    }

    const authRes = data as AuthResponse;
    saveAuthData(authRes.access_token, authRes.user);
    return authRes;
  },

  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const baseUrl = getApiBaseUrl();
    const res = await fetch(`${baseUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password, role: "user" }),
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.error?.message || data.detail || "Registration failed. Please check your inputs.";
      throw new Error(msg);
    }

    const authRes = data as AuthResponse;
    saveAuthData(authRes.access_token, authRes.user);
    return authRes;
  },

  logout: (): void => {
    clearAuthData();
  },
};
