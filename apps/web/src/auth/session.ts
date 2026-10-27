export type SupabaseUser = {
  id: string;
  email?: string | null;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: SupabaseUser;
};

type AuthResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  expires_at?: number;
  user?: SupabaseUser;
  msg?: string;
  message?: string;
  error_description?: string;
  error?: string;
};

const SUPABASE_URL = String(import.meta.env.VITE_SUPABASE_URL || "").replace(/\/+$/, "");
const SUPABASE_PUBLISHABLE_KEY = String(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "");
const SESSION_KEY = "charterpulse.auth.session.v1";
const ACTIVE_USER_KEY = "charterpulse.activeUserId";

let activeSession: AuthSession | null = null;
const listeners = new Set<(session: AuthSession | null) => void>();

export function isAuthConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY && /^https:\/\//i.test(SUPABASE_URL));
}

export function subscribeToSession(listener: (session: AuthSession | null) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notifySession(session: AuthSession | null): void {
  for (const listener of listeners) listener(session);
}

function readStoredSession(): AuthSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<AuthSession>;
    if (typeof value.access_token !== "string" || typeof value.refresh_token !== "string" ||
        typeof value.expires_at !== "number" || typeof value.user?.id !== "string") {
      sessionStorage.removeItem(SESSION_KEY);
      return null;
    }
    return value as AuthSession;
  } catch {
    return null;
  }
}

function saveSession(session: AuthSession | null): void {
  activeSession = session;
  try {
    if (session) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
      sessionStorage.setItem(ACTIVE_USER_KEY, session.user.id);
    } else {
      sessionStorage.removeItem(SESSION_KEY);
      sessionStorage.removeItem(ACTIVE_USER_KEY);
    }
  } catch {
    // Never downgrade API calls to anonymous access if storage is unavailable.
  }
  notifySession(session);
}

function errorMessage(body: AuthResponse, statusCode: number): string {
  return body.error_description || body.msg || body.message || body.error ||
    (statusCode === 400 ? "Check your email and password, then try again." : "Authentication failed (HTTP " + statusCode + ").");
}

async function authRequest(path: string, payload: Record<string, string>): Promise<AuthResponse> {
  if (!isAuthConfigured()) {
    throw new Error("Supabase Auth is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in the frontend environment.");
  }
  let response: Response;
  try {
    response = await fetch(SUPABASE_URL + "/auth/v1/" + path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": SUPABASE_PUBLISHABLE_KEY,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("Cannot reach Supabase authentication. Check your network connection.");
  }
  let body: AuthResponse = {};
  try {
    body = await response.json() as AuthResponse;
  } catch {
    body = {};
  }
  if (!response.ok) throw new Error(errorMessage(body, response.status));
  return body;
}

function sessionFromResponse(response: AuthResponse): AuthSession | null {
  if (!response.access_token || !response.refresh_token || !response.user?.id) return null;
  const expiresAt = typeof response.expires_at === "number"
    ? response.expires_at
    : Math.floor(Date.now() / 1000) + Math.max(60, Number(response.expires_in || 3600));
  return {
    access_token: response.access_token,
    refresh_token: response.refresh_token,
    expires_at: expiresAt,
    user: response.user,
  };
}

export async function signIn(email: string, password: string): Promise<AuthSession> {
  const response = await authRequest("token?grant_type=password", { email, password });
  const session = sessionFromResponse(response);
  if (!session) throw new Error("Supabase did not return a complete login session.");
  saveSession(session);
  return session;
}

export async function signUp(email: string, password: string): Promise<{ session: AuthSession | null; confirmationRequired: boolean }> {
  const response = await authRequest("signup", { email, password });
  const session = sessionFromResponse(response);
  if (session) saveSession(session);
  return { session, confirmationRequired: !session };
}

async function refreshSession(current: AuthSession): Promise<AuthSession> {
  const response = await authRequest("token?grant_type=refresh_token", {
    refresh_token: current.refresh_token,
  });
  const session = sessionFromResponse(response);
  if (!session) throw new Error("Supabase could not refresh your session. Sign in again.");
  saveSession(session);
  return session;
}

export async function restoreSession(): Promise<AuthSession | null> {
  if (!isAuthConfigured()) return null;
  activeSession = readStoredSession();
  if (!activeSession) return null;
  if (activeSession.expires_at <= Math.floor(Date.now() / 1000) + 60) {
    try {
      return await refreshSession(activeSession);
    } catch {
      saveSession(null);
      return null;
    }
  }
  saveSession(activeSession);
  return activeSession;
}

export async function getAccessToken(): Promise<string> {
  if (!isAuthConfigured()) {
    throw new Error("Supabase Auth is not configured. Ask an administrator to configure the frontend environment.");
  }
  const current = activeSession || readStoredSession();
  if (!current) throw new Error("Your session has expired. Sign in to continue.");
  if (current.expires_at > Math.floor(Date.now() / 1000) + 60) {
    activeSession = current;
    return current.access_token;
  }
  try {
    return (await refreshSession(current)).access_token;
  } catch {
    saveSession(null);
    throw new Error("Your session has expired. Sign in again to continue.");
  }
}

export async function signOut(): Promise<void> {
  const current = activeSession || readStoredSession();
  saveSession(null);
  if (!current || !isAuthConfigured()) return;
  try {
    await fetch(SUPABASE_URL + "/auth/v1/logout", {
      method: "POST",
      headers: {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": "Bearer " + current.access_token,
      },
    });
  } catch {
    // Local session is already cleared.
  }
}

export function getActiveUserId(): string | null {
  try {
    return sessionStorage.getItem(ACTIVE_USER_KEY);
  } catch {
    return null;
  }
}
