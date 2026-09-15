"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin, adminMe, signup, setToken, setRole, getToken, clearAuth } from "@/lib/api";

type AuthState = "checking" | "authenticated" | "anonymous";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>("checking");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      void Promise.resolve().then(() => setState("anonymous"));
      return;
    }
    adminMe()
      .then((me) => {
        setRole(me.role);
        setState("authenticated");
      })
      .catch(() => {
        clearAuth();
        setState("anonymous");
      });
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result =
        mode === "login"
          ? await adminLogin(email.trim(), password)
          : await signup(email.trim(), name.trim(), password);
      setToken(result.token);
      setRole(result.role);
      setState("authenticated");
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  if (state === "checking") {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-gray-500">Checking session…</p>
      </div>
    );
  }

  if (state === "anonymous") {
    const subtitle =
      mode === "login"
        ? "Sign in to the KreatOS console."
        : "Create an account to start exploring creator intelligence.";
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <form
          onSubmit={submit}
          className="w-full max-w-sm rounded-2xl border border-gray-800 bg-gray-900 p-8"
        >
          <h1 className="text-2xl font-bold tracking-tight text-white">KreatOS</h1>
          <p className="mt-1 text-sm text-gray-400">{subtitle}</p>

          {error && (
            <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {mode === "signup" && (
            <>
              <label className="mt-6 block text-xs font-medium text-gray-400">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
                placeholder="Your name (optional)"
              />
            </>
          )}

          <label className="mt-6 block text-xs font-medium text-gray-400">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
            placeholder="you@example.com"
          />

          <label className="mt-4 block text-xs font-medium text-gray-400">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "signup" ? 8 : undefined}
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
            placeholder={mode === "signup" ? "At least 8 characters" : "••••••••"}
          />

          <button
            type="submit"
            disabled={busy}
            className="mt-6 w-full rounded-lg bg-white py-3 text-sm font-medium text-black disabled:opacity-50"
          >
            {busy
              ? mode === "login"
                ? "Signing in…"
                : "Creating account…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
            }}
            className="mt-4 w-full text-center text-xs text-gray-500 hover:text-gray-300"
          >
            {mode === "login"
              ? "New here? Create an account"
              : "Already have an account? Sign in"}
          </button>
        </form>
      </div>
    );
  }

  return <>{children}</>;
}