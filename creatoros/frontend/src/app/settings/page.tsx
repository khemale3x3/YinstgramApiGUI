"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Err, Input, PageHeader, Btn, Loader } from "@/components/ui";
import {
  adminFeatures,
  adminSetFeature,
  adminMe,
  databaseStatus,
  getSettings,
  updateSettings,
  storageStatus,
  type FeatureFlag,
  type Settings,
} from "@/lib/api";

export default function SettingsPage() {
  const [app, setApp] = useState<Settings | null>(null);
  const [patch, setPatch] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [features, setFeatures] = useState<FeatureFlag[]>([]);
  const [myRole, setMyRole] = useState("admin");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [testing, setTesting] = useState(false);
  const [testMessage, setTestMessage] = useState("");

  useEffect(() => {
    getSettings().then(setApp).catch((e) => setError(e.message));
    adminMe()
      .then((me) => setMyRole(me.role))
      .catch(() => {});
    adminFeatures()
      .then((list) => setFeatures(list))
      .catch(() => {});
  }, []);

  function set(key: string, value: unknown) {
    setPatch((p) => ({ ...p, [key]: value }));
  }

  function toggleSection(key: string) {
    setCollapsed((current) => ({ ...current, [key]: !current[key] }));
  }

  async function testConnections() {
    setTesting(true);
    setTestMessage("");
    try {
      const [db, storageStatusResult] = await Promise.all([databaseStatus(), storageStatus()]);
      setTestMessage(`Database: ${db.local.available ? "connected" : "unavailable"}. SQL Server: ${db.remote.available ? "connected" : "unavailable"}. Storage: ${storageStatusResult.available ? "connected" : "unavailable"}.`);
    } catch (e) {
      setTestMessage(e instanceof Error ? e.message : "Connection test failed");
    } finally {
      setTesting(false);
    }
  }

  async function toggleFeature(feature: FeatureFlag) {
    setBusy(true);
    setError("");
    try {
      const updated = await adminSetFeature(feature.key, !feature.enabled);
      setFeatures((current) => current.map((item) => item.key === updated.key ? updated : item));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update feature access");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (Object.keys(patch).length === 0) return;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const flat: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(patch)) {
        flat[key] = value;
      }
      await updateSettings(flat);
      setSaved(true);
      const fresh = await getSettings();
      setApp(fresh);
      setPatch({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  }

  if (!app) return error ? <PageHeader title="Settings" /> : <Loader />;

  const scraper = (patch.scraper as Partial<Settings["scraper"]> | undefined) ?? app.scraper;
  const database = app.database;
  const postgres = app.postgres;
  const storage = app.storage;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <PageHeader title="Settings" subtitle="Runtime configuration — saved to backend/.env on change." />
        <div className="flex gap-2"><Btn onClick={() => void testConnections()} disabled={testing}>{testing ? "Testing…" : "Test connections"}</Btn><Btn primary onClick={save} disabled={busy || Object.keys(patch).length === 0}>{busy ? "Saving…" : "Save changes"}</Btn></div>
      </div>

      {error && <div className="mb-6"><Err message={error} /></div>}
      {saved && (
        <div className="mb-6 rounded-lg border border-emerald-800 bg-emerald-950/50 p-3 text-sm text-emerald-300">
          Settings saved.
        </div>
      )}
      {testMessage && <div className="mb-6 rounded-lg border border-blue-900 bg-blue-950/30 p-3 text-sm text-blue-300">{testMessage}</div>}

      <div className="grid gap-6">
        <Collapsible title="General" sectionKey="general" collapsed={collapsed.general} onToggle={toggleSection}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              value={String(app.admin_email)}
              onChange={(v) => set("admin_email", v)}
              placeholder="Admin email"
            />
            <Input
              value={String(app.jwt_expires_minutes)}
              onChange={(v) => set("jwt_expires_minutes", Number(v))}
              placeholder="Token expiry (minutes)"
              type="number"
            />
            <Input
              value={app.cors_origins.join(", ")}
              onChange={(v) => set("cors_origins", v.split(",").map((s) => s.trim()).filter(Boolean))}
              placeholder="Allowed origins (comma-separated)"
            />
            <Input
              value={app.export_formats.join(", ")}
              onChange={(v) => set("export_formats", v.split(",").map((s) => s.trim()).filter(Boolean))}
              placeholder="Export formats (json, jsonl, csv)"
            />
          </div>
        </Collapsible>

        <Collapsible title="Scraper (Selenium + sessions)" sectionKey="scraper" collapsed={collapsed.scraper} onToggle={toggleSection}>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              value={String(scraper.max_workers)}
              onChange={(v) => setScraper("max_workers", Number(v))}
              type="number"
              placeholder="Max workers"
            />
            <Input
              value={String(scraper.max_posts)}
              onChange={(v) => setScraper("max_posts", Number(v))}
              type="number"
              placeholder="Max posts"
            />
            <Input
              value={String(scraper.active_sessions)}
              onChange={(v) => setScraper("active_sessions", Number(v))}
              type="number"
              placeholder="Active sessions"
            />
            <Input
              value={String(scraper.timeout)}
              onChange={(v) => setScraper("timeout", Number(v))}
              type="number"
              placeholder="Timeout (s)"
            />
            <Input
              value={String(scraper.max_test_profiles)}
              onChange={(v) => setScraper("max_test_profiles", Number(v))}
              type="number"
              placeholder="Test-mode limit"
            />
          </div>
          <div className="mt-4 space-y-2">
            <Toggle
              label="Run the scraper headless"
              checked={Boolean(scraper.headless)}
              onChange={(v) => setScraper("headless", v)}
            />
            <Toggle
              label="Test mode (limit to a few profiles)"
              checked={Boolean(scraper.test_mode)}
              onChange={(v) => setScraper("test_mode", v)}
            />
          </div>
        </Collapsible>

        <Collapsible title="PostgreSQL (app store)" sectionKey="postgres" collapsed={collapsed.postgres} onToggle={toggleSection}>
          <p className="mb-4 text-xs text-gray-500">
            KreatOS runtime database — jobs, projects, users, features, menus,
            audit trail and scraped profiles. Schema is auto-created on boot from
            <span className="font-mono"> data/postgres/*.sql</span> (pgAdmin: localhost:5432,
            database <span className="font-mono">yinstagram</span>, schema{" "}
            <span className="font-mono">{postgres.schema}</span>).
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              value={String(patch.pg_host ?? postgres.host ?? "")}
              onChange={(v) => set("pg_host", v)}
              placeholder="Host (localhost)"
            />
            <Input
              value={String(patch.pg_port ?? postgres.port ?? 5432)}
              onChange={(v) => set("pg_port", Number(v))}
              type="number"
              placeholder="Port"
            />
            <Input
              value={String(patch.pg_user ?? "")}
              onChange={(v) => set("pg_user", v)}
              placeholder="User"
            />
            <Input
              value={String(patch.pg_password ?? "")}
              onChange={(v) => set("pg_password", v)}
              placeholder="Password"
              type="password"
            />
            <Input
              value={String(patch.pg_name ?? postgres.name ?? "")}
              onChange={(v) => set("pg_name", v)}
              placeholder="Database"
            />
            <Input
              value={String(patch.pg_schema ?? postgres.schema ?? "")}
              onChange={(v) => set("pg_schema", v)}
              placeholder="Schema"
            />
          </div>
          <div className="mt-3">
            <Toggle
              label="Use PostgreSQL as the primary store"
              checked={Boolean(patch.pg_enabled ?? postgres.enabled)}
              onChange={(v) => set("pg_enabled", v)}
            />
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Status:{" "}
            <span className={postgres.configured ? "text-emerald-400" : "text-amber-400"}>
              {postgres.configured ? "configured" : "not configured (set PG_PASSWORD in .env)"}
            </span>
          </p>
        </Collapsible>

        <Collapsible title="SQL Server ingest" sectionKey="sqlserver" collapsed={collapsed.sqlserver} onToggle={toggleSection}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              value={String(patch.db_server ?? app.database.server ?? "")}
              onChange={(v) => set("db_server", v)}
              placeholder="Server"
            />
            <Input
              value={String(patch.db_name ?? app.database.name ?? "")}
              onChange={(v) => set("db_name", v)}
              placeholder="Database"
            />
            <Input
              value={String(patch.db_user ?? app.database.user ?? "")}
              onChange={(v) => set("db_user", v)}
              placeholder="User"
            />
            <Input
              value={String(patch.db_password ?? "")}
              onChange={(v) => set("db_password", v)}
              placeholder="Password"
              type="password"
            />
            <Input
              value={String(patch.db_table ?? app.database.table ?? "")}
              onChange={(v) => set("db_table", v)}
              placeholder="Table"
            />
            <Input
              value={String(patch.db_driver ?? app.database.driver ?? "")}
              onChange={(v) => set("db_driver", v)}
              placeholder="ODBC driver"
            />
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Status: <span className={database.configured ? "text-emerald-400" : "text-amber-400"}>
              {database.configured ? "configured" : "not configured (set DB_PASSWORD in .env)"}
            </span>
          </p>
        </Collapsible>

        <Collapsible title="S3 storage" sectionKey="s3" collapsed={collapsed.s3} onToggle={toggleSection}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              value={String(patch.s3_bucket ?? app.storage.bucket ?? "")}
              onChange={(v) => set("s3_bucket", v)}
              placeholder="Bucket"
            />
            <Input
              value={String(patch.s3_region ?? app.storage.region ?? "")}
              onChange={(v) => set("s3_region", v)}
              placeholder="Region"
            />
            <Input
              value={String(patch.s3_access_key ?? "")}
              onChange={(v) => set("s3_access_key", v)}
              placeholder="Access key"
            />
            <Input
              value={String(patch.s3_secret_key ?? "")}
              onChange={(v) => set("s3_secret_key", v)}
              placeholder="Secret key"
              type="password"
            />
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Status: <span className={storage.configured ? "text-emerald-400" : "text-amber-400"}>
              {storage.configured ? "configured" : "not configured (set S3 keys in .env)"}
            </span>
          </p>
        </Collapsible>

        <Collapsible title="Scraped data destination" sectionKey="destination" collapsed={collapsed.destination} onToggle={toggleSection}>
          <p className="mb-4 text-xs text-gray-500">
            Choose where scraper artifacts should be saved. Local and S3 are available now;
            GCP and Drive fields are saved for their provider adapters.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-400">Provider</span>
              <select
                value={String(patch.storage_provider ?? storage.provider)}
                onChange={(e) => set("storage_provider", e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white"
              >
                <option value="local">Local storage</option>
                <option value="s3">Amazon S3 / S3-compatible</option>
                <option value="gcs">Google Cloud Storage</option>
                <option value="drive">Google Drive</option>
              </select>
            </label>
            <Input value={String(patch.storage_local_dir ?? storage.local_dir)} onChange={(v) => set("storage_local_dir", v)} placeholder="Local directory" />
            <Input value={String(patch.gcs_bucket ?? storage.gcs_bucket)} onChange={(v) => set("gcs_bucket", v)} placeholder="GCP bucket" />
            <Input value={String(patch.gcs_project ?? storage.gcs_project)} onChange={(v) => set("gcs_project", v)} placeholder="GCP project ID" />
            <Input value={String(patch.drive_folder_id ?? storage.drive_folder_id)} onChange={(v) => set("drive_folder_id", v)} placeholder="Google Drive folder ID" />
          </div>
        </Collapsible>

        <Collapsible title="Rights & access" sectionKey="rights" collapsed={collapsed.rights} onToggle={toggleSection}>
          <p className="mb-3 text-xs text-gray-500">
            Every feature is enforced on the backend (403 before a route runs) and
            mirrored here from the feature table — view only.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="py-2 pr-4 font-medium">Feature</th>
                  <th className="py-2 pr-4 font-medium">Group</th>
                  <th className="py-2 pr-4 font-medium">Allowed roles</th>
                  <th className="py-2 font-medium">Your access ({myRole})</th>
                </tr>
              </thead>
              <tbody>
                {features.map((f) => {
                  const roles = (f.roles || "admin,user").split(",").map((r) => r.trim());
                  return (
                    <tr key={f.key} className="border-b border-gray-900">
                      <td className="py-2 pr-4 text-gray-200">
                        {f.label}
                        <span className="ml-2 font-mono text-xs text-gray-600">{f.key}</span>
                      </td>
                      <td className="py-2 pr-4 text-gray-500">{f.group}</td>
                      <td className="py-2 pr-4">
                        {roles.map((r) => (
                          <span
                            key={r}
                            className="mr-1 rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-300"
                          >
                            {r}
                          </span>
                        ))}
                      </td>
                      <td className="py-2">
                        <span
                          className={
                            f.enabled && roles.includes(myRole)
                              ? "text-emerald-400"
                              : "text-gray-600"
                          }
                        >
                          {f.enabled && roles.includes(myRole) ? "enabled" : !f.enabled ? "disabled" : "no access"}
                        </span>
                        <button type="button" onClick={() => void toggleFeature(f)} disabled={busy} className="ml-3 rounded border border-gray-700 px-2 py-1 text-[11px] text-gray-300 hover:bg-gray-800 disabled:opacity-50">{f.enabled ? "Disable" : "Enable"}</button>
                      </td>
                    </tr>
                  );
                })}
                {features.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-gray-500">
                      Feature table unavailable.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Collapsible>

        <Collapsible title="System" sectionKey="system" collapsed={collapsed.system} onToggle={toggleSection}>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <Row label="Application" value={app.app_name} />
            <Row label="Version" value={app.app_version} />
            <Row label="Debug mode" value={app.debug ? "on" : "off"} />
            <Row label="Admin email" value={app.admin_email} />
            <Row label="Data directory" value={app.data_dir} />
            <Row label="Session directory" value={app.session_dir} />
            <Row label="Pipeline directory" value={app.pipeline_dir} />
            <Row
              label="Scraper delay range (s)"
              value={app.scraper.delay_range.join(" – ")}
            />
          </dl>
        </Collapsible>

      </div>
    </div>
  );

  function setScraper<K extends keyof NonNullable<Settings["scraper"]>>(key: K, value: unknown) {
    const flatKey = `scraper_${key}` as keyof Settings;
    set(flatKey, value);
  }
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-gray-500">{label}</dt>
      <dd className="truncate font-mono text-xs text-gray-200">{value}</dd>
    </div>
  );
}

function Collapsible({ title, sectionKey, collapsed, onToggle, children }: { title: string; sectionKey: string; collapsed?: boolean; onToggle: (key: string) => void; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-gray-800 bg-gray-900/50">
      <button type="button" onClick={() => onToggle(sectionKey)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-900/70">
        <span className="text-sm font-semibold text-gray-200">{title}</span>
        <span className={`text-gray-500 transition-transform ${collapsed ? "" : "rotate-180"}`}>▾</span>
      </button>
      {!collapsed && <div className="border-t border-gray-800 p-5">{children}</div>}
    </section>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="accent-white" />
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  );
}