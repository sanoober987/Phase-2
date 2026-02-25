// frontend/lib/auth.ts

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

// Fallback uses 127.0.0.1 explicitly — browsers resolve "localhost" via DNS
// which can differ from what the backend binds to (127.0.0.1 loopback).
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface User {
  id: string;
  email: string;
}

// ─── Cookie helpers (middleware reads cookies, not localStorage) ──────────────

function setCookieToken(token: string, expiresIn: number) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + expiresIn * 1000).toUTCString();
  // SameSite=Lax is safe for same-origin; Secure is set by the browser on HTTPS
  document.cookie = `${TOKEN_KEY}=${token}; path=/; expires=${expires}; SameSite=Lax`;
}

function clearCookieToken() {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`;
}

// ─── Auth API calls ───────────────────────────────────────────────────────────

/**
 * Login: call the backend /auth/login endpoint, store token + user.
 * Returns { user } on success.
 */
export async function login(
  email: string,
  password: string
): Promise<{ user: User }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error(
      "Cannot reach the server. Make sure the backend is running on " + API_BASE_URL
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((e: { msg: string }) => e.msg).join(", ")
        : "Invalid credentials";
    throw new Error(message);
  }

  const data = await response.json();
  const token: string = data.access_token;
  const expiresIn: number = data.expires_in || 3600;

  const user = decodeTokenUser(token, email);

  storeAuth(token, user, expiresIn);

  return { user };
}

/**
 * Sign up: call the backend /auth/register endpoint, store token + user.
 * Returns { user } on success.
 */
export async function signUp(
  email: string,
  password: string
): Promise<{ user: User }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error(
      "Cannot reach the server. Make sure the backend is running on " + API_BASE_URL
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((e: { msg: string }) => e.msg).join(", ")
        : "Registration failed";
    throw new Error(message);
  }

  const data = await response.json();
  const token: string = data.access_token;
  const expiresIn: number = data.expires_in || 3600;

  const user = decodeTokenUser(token, email);

  storeAuth(token, user, expiresIn);

  return { user };
}

// ─── Token storage ────────────────────────────────────────────────────────────

function storeAuth(token: string, user: User, expiresIn: number) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Mirror to cookie so Next.js middleware can read it for route protection
  setCookieToken(token, expiresIn);
}

/** Logout: clear stored token and user. */
export function logout() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  clearCookieToken();
}

// ─── Auth state ───────────────────────────────────────────────────────────────

/** Check if user is authenticated by reading localStorage. */
export function checkAuthState(): {
  isAuthenticated: boolean;
  user: User | null;
} {
  if (typeof window === "undefined")
    return { isAuthenticated: false, user: null };

  const token = localStorage.getItem(TOKEN_KEY);
  const userJson = localStorage.getItem(USER_KEY);

  if (!token) return { isAuthenticated: false, user: null };

  // Check if token is expired
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      logout();
      return { isAuthenticated: false, user: null };
    }
  } catch {
    logout();
    return { isAuthenticated: false, user: null };
  }

  let user: User | null = null;
  if (userJson) {
    try {
      user = JSON.parse(userJson) as User;
    } catch {
      // Corrupted user entry — clear everything and re-authenticate
      logout();
      return { isAuthenticated: false, user: null };
    }
  }

  return { isAuthenticated: true, user };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Decode JWT payload (without verification — verification is server-side).
 * Extracts user id (sub) and email.
 */
function decodeTokenUser(token: string, fallbackEmail: string): User {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      id: payload.sub || "",
      email: payload.email || fallbackEmail,
    };
  } catch {
    return { id: "", email: fallbackEmail };
  }
}

/** Get the stored JWT token. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** Get the Authorization header value for API requests. */
export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/** Redirect to login. */
export function redirectToLogin() {
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/** Get user ID from stored user. */
export function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  const userJson = localStorage.getItem(USER_KEY);
  if (!userJson) return null;
  const user: User = JSON.parse(userJson);
  return user.id;
}
