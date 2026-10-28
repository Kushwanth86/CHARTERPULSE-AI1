import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  isAuthConfigured,
  restoreSession,
  signIn,
  signOut,
  signUp,
  subscribeToSession,
  type AuthSession,
} from "./session";
import "./auth.css";

type AuthGateProps = { children: ReactNode };

export default function AuthGate({ children }: AuthGateProps) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(false);
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let mounted = true;
    const unsubscribe = subscribeToSession(next => {
      if (mounted) setSession(next);
    });
    restoreSession()
      .then(restored => { if (mounted) setSession(restored); })
      .finally(() => { if (mounted) setReady(true); });
    return () => {
      mounted = false;
      unsubscribe();
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "signin") {
        await signIn(email.trim(), password);
      } else {
        const result = await signUp(email.trim(), password);
        if (result.confirmationRequired) {
          setMode("signin");
          setPassword("");
          setNotice("Account request sent. Check your email to confirm, then sign in.");
        } else {
          setNotice("Account created and signed in.");
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await signOut();
    setPassword("");
    setError("");
    setNotice("");
    try {
      localStorage.removeItem("charterpulse.frontend.audit.v1");
    } catch {
      // Optional browser-side audit cache.
    }
  }

  if (!isAuthConfigured()) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="auth-brand">CHARTERPULSE AI</div>
          <h1>Authentication setup required</h1>
          <p>The frontend is not configured with the Supabase project URL and publishable key.</p>
          <p className="auth-setup-hint">Configure VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in the Vercel project environment, then redeploy the frontend.</p>
        </section>
      </main>
    );
  }

  if (!ready) {
    return <main className="auth-page"><section className="auth-card"><div className="auth-brand">CHARTERPULSE AI</div><p>Restoring secure session…</p></section></main>;
  }

  if (session) {
    return (
      <div className="auth-app-shell">
        <div className="auth-session-bar">
          <span>Signed in as <strong>{session.user.email || session.user.id}</strong></span>
          <button type="button" onClick={() => void logout()}>Sign out</button>
        </div>
        {children}
      </div>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">CHARTERPULSE AI</div>
        <p className="auth-eyebrow">SECURE PROCUREMENT WORKSPACE</p>
        <h1>{mode === "signin" ? "Sign in" : "Create account"}</h1>
        <p className="auth-subtitle">Sign in to access saved procurement requirements, decisions, and private market entries.</p>
        <form onSubmit={submit}>
          <label htmlFor="auth-email">Email</label>
          <input id="auth-email" type="email" autoComplete="email" required value={email}
            onChange={event => setEmail(event.target.value)} placeholder="you@company.com" />
          <label htmlFor="auth-password">Password</label>
          <input id="auth-password" type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            minLength={8} required value={password}
            onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters" />
          {error && <p className="auth-message auth-error" role="alert">{error}</p>}
          {notice && <p className="auth-message auth-notice" role="status">{notice}</p>}
          <button className="auth-primary" type="submit" disabled={busy}>
            {busy ? "Please wait…" : mode === "signin" ? "Sign in securely" : "Create account"}
          </button>
        </form>
        <div className="auth-mode-switch">
          {mode === "signin" ? "New to CharterPulse?" : "Already have an account?"}{" "}
          <button type="button" onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError("");
            setNotice("");
          }}>{mode === "signin" ? "Create account" : "Sign in"}</button>
        </div>
      </section>
    </main>
  );
}
