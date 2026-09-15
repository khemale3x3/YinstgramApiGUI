"use client";

import { useEffect, useState } from "react";
import {
  addAccount,
  checkAccount,
  getAccount,
  listAccounts,
  removeAccount,
  type Account,
} from "@/lib/api";

const STATUS_LABELS: Record<Account["status"], string> = {
  ready: "Ready",
  no_session: "No session",
  invalid: "Invalid",
};

const STATUS_COLORS: Record<Account["status"], string> = {
  ready: "text-emerald-400",
  no_session: "text-amber-400",
  invalid: "text-red-400",
};

const STATUS_DOTS: Record<Account["status"], string> = {
  ready: "bg-emerald-500",
  no_session: "bg-amber-500",
  invalid: "bg-red-500",
};

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<string[]>([]);
  const [details, setDetails] = useState<Record<string, Account>>({});
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    kind: "ok" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const { accounts: names } = await listAccounts();
        if (cancelled) return;
        setAccounts(names);
        const results = await Promise.all(names.map((name) => getAccount(name)));
        if (cancelled) return;
        setDetails(
          Object.fromEntries(results.map((account) => [account.username, account])),
        );
      } catch (err) {
        if (cancelled) return;
        setMessage({
          kind: "error",
          text: err instanceof Error ? err.message : "Failed to load accounts",
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh(name: string) {
    const account = await getAccount(name);
    setDetails((prev) => ({ ...prev, [name]: account }));
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setBusy(true);
    setMessage(null);
    try {
      const account = await addAccount(username.trim().replace(/^@/, ""), password);
      setPassword("");
      setUsername("");
      setDetails((prev) => ({ ...prev, [account.username]: account }));
      setAccounts((prev) =>
        prev.includes(account.username)
          ? prev
          : [...prev, account.username],
      );
      setMessage({ kind: "ok", text: "Account added. Session saved." });
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "Login failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleCheck(name: string) {
    setChecking(name);
    setMessage(null);
    try {
      const result = await checkAccount(name);
      await refresh(name);
      setMessage({
        kind: result.verified ? "ok" : "error",
        text: `${result.verified ? "Verified" : "Not verified"}: ${result.message}`,
      });
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "Check failed",
      });
    } finally {
      setChecking(null);
    }
  }

  async function handleRemove(name: string) {
    if (!confirm(`Remove session for @${name}?`)) return;
    try {
      await removeAccount(name);
      setAccounts((prev) => prev.filter((a) => a !== name));
      setDetails((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
      setMessage({ kind: "ok", text: `Session for @${name} removed.` });
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "Remove failed",
      });
    }
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold tracking-tight text-white">Accounts</h1>
      <p className="text-gray-400 mt-1">
        Manage Instagram accounts and their persisted sessions.
      </p>

      {message && (
        <div
          className={
            message.kind === "ok"
              ? "mt-6 rounded-lg border border-emerald-900 bg-emerald-950/50 p-4 text-sm text-emerald-300"
              : "mt-6 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300"
          }
        >
          {message.text}
        </div>
      )}

      <form
        onSubmit={handleAdd}
        className="mt-8 rounded-xl border border-gray-800 bg-gray-900 p-6"
      >
        <h2 className="text-lg font-semibold text-white">Add Account</h2>
        <p className="mt-1 text-xs text-gray-500">
          Credentials are used once to authenticate; the session is then saved
          locally and reused. Passwords are never stored and sessions are
          gitignored — treat them as secrets.
        </p>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Instagram username"
            className="rounded-lg bg-gray-950 border border-gray-700 px-4 py-3 text-sm placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="rounded-lg bg-gray-950 border border-gray-700 px-4 py-3 text-sm placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
          />
        </div>

        <button
          type="submit"
          disabled={busy || !username.trim() || !password}
          className="mt-4 rounded-lg bg-white text-black px-5 py-2.5 text-sm font-medium disabled:opacity-50"
        >
          {busy ? "Adding..." : "Add Account"}
        </button>
      </form>

      <h2 className="mt-10 text-lg font-semibold text-white">Connected</h2>
      <div className="mt-3 overflow-hidden rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-left text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-4 py-3">Account</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Session</th>
              <th className="px-4 py-3">Last Check</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {accounts.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-600">
                  No accounts added yet.
                </td>
              </tr>
            ) : (
              accounts.map((name) => {
                const account = details[name];
                const status = account?.status ?? "no_session";
                return (
                  <tr key={name} className="bg-gray-950">
                    <td className="px-4 py-3 font-medium text-white">@{name}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 ${STATUS_COLORS[status]}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[status]}`} />
                        {STATUS_LABELS[status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {account?.has_session ? "Saved" : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {account?.last_checked
                        ? new Date(account.last_checked).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleCheck(name)}
                        disabled={checking === name}
                        className="rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-900 disabled:opacity-50"
                      >
                        {checking === name ? "Checking…" : "Check Session"}
                      </button>
                      <button
                        onClick={() => handleRemove(name)}
                        className="ml-2 rounded-lg border border-red-900 px-3 py-1.5 text-xs text-red-400 hover:bg-red-950"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {details && Object.values(details).some((d) => d.last_error) && (
        <p className="mt-4 text-xs text-gray-500">
          {Object.values(details)
            .filter((d) => d.last_error)
            .map((d) => `@${d.username}: ${d.last_error}`)
            .join(" · ")}
        </p>
      )}
    </div>
  );
}