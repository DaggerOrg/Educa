import { useState, type FormEvent } from "react";
import { logIn, signUp, type Session } from "../auth.ts";
import type { Role } from "../types.ts";

interface AuthProps {
  onAuthenticated: (session: Session) => void;
}

type Mode = "login" | "signup";

export default function Auth({ onAuthenticated }: AuthProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("student");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const session = mode === "login" ? await logIn(email, password) : await signUp(email, password, name, role);
      onAuthenticated(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="wordmark auth-wordmark">EDUCA<span>.</span></div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab${mode === "login" ? " is-active" : ""}`}
            onClick={() => switchMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={`auth-tab${mode === "signup" ? " is-active" : ""}`}
            onClick={() => switchMode("signup")}
          >
            Sign up
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <>
              <label className="field-label" htmlFor="auth-name">Name</label>
              <input
                id="auth-name"
                className="auth-input"
                type="text"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </>
          )}

          <label className="field-label" htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            className="auth-input"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label className="field-label" htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            className="auth-input"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "signup" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {mode === "signup" && (
            <>
              <span className="field-label">I am a...</span>
              <div className="auth-role-toggle">
                <button
                  type="button"
                  className={`auth-role-btn${role === "student" ? " is-active" : ""}`}
                  onClick={() => setRole("student")}
                >
                  Student
                </button>
                <button
                  type="button"
                  className={`auth-role-btn${role === "teacher" ? " is-active" : ""}`}
                  onClick={() => setRole("teacher")}
                >
                  Teacher
                </button>
              </div>
            </>
          )}

          {error && <div className="error-banner auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
