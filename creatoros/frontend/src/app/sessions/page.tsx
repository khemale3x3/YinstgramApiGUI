"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Btn, Card, Empty, Err, Loader, PageHeader, StatusBadge } from "@/components/ui";
import {
  getSessions,
  importSessionsEnv,
  type SessionCounts,
  type SessionRecord,
} from "@/lib/api";

export default function SessionsPage() {
  const [counts, setCounts] = useState<SessionCounts | null>(null);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getSessions();
      setCounts(data.counts);
      setSessions(data.sessions);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getSessions()
      .then((data) => {
        setCounts(data.counts);
        setSessions(data.sessions);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sessions"))
      .finally(() => setLoading(false));
  }, []);

  async function handleImport(file: File) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await importSessionsEnv(file);
      setNotice(`Imported ${result.imported} INSTA_SESSION_*/INSTA_ACCOUNT_* entry(ies) into backend/.env.`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to import env file");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loader />;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Sessions"
        subtitle="Instagram cookie sessions and instagrapi JSON sessions used for scraping."
      />

      {error && <div className="mb-6"><Err message={error} /></div>}
      {notice && (
        <div className="mb-6 rounded-lg border border-emerald-800 bg-emerald-950/50 p-3 text-sm text-emerald-300">
          {notice}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-4 mb-8">
        <Stat label="Cookie total" value={counts?.cookie_total ?? 0} />
        <Stat label="Active" value={counts?.cookie_active ?? 0} />
        <Stat label="Backup pool" value={counts?.cookie_backup ?? 0} />
        <Stat label="Instagrapi" value={counts?.instagrapi ?? 0} />
      </div>

      <Card title="Import sessions from .env" className="mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <p className="flex-1 text-sm text-gray-400">
            Upload a file containing <code className="text-gray-300">INSTA_SESSION_1=...</code> and{" "}
            <code className="text-gray-300">INSTA_ACCOUNT_1=user:pass</code> entries. The first{" "}
            <span className="text-gray-300">active-sessions</span> entries form the active pool; the rest
            are backups.
          </p>
          <Btn onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? "Importing…" : "Choose .env file"}
          </Btn>
          <input
            ref={fileRef}
            type="file"
            accept=".env,.txt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImport(f);
              e.target.value = "";
            }}
          />
        </div>
      </Card>

      {sessions.length === 0 ? (
        <Empty label="No sessions configured yet." />
      ) : (
        <Card title="Configured sessions">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-gray-500 border-b border-gray-800">
                <tr>
                  <th className="py-2 pr-3">Label</th>
                  <th className="py-2 pr-3">Kind</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2">Preview</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session, i) => (
                  <tr key={session.key ?? i} className="border-b border-gray-800/60">
                    <td className="py-2 pr-3 text-gray-200">{session.label}</td>
                    <td className="py-2 pr-3 capitalize text-gray-400">{session.kind}</td>
                    <td className="py-2 pr-3">
                      {session.kind === "cookie" ? (
                        session.active ? (
                          <StatusBadge label="active" tone="green" />
                        ) : (
                          <StatusBadge label="backup" tone="amber" />
                        )
                      ) : (
                        <StatusBadge label={session.status ?? "saved"} tone="blue" />
                      )}
                    </td>
                    <td className="py-2 font-mono text-xs text-gray-500">{session.preview}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{label}</p>
    </div>
  );
}