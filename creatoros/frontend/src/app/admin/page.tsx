"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, Err, Loader, PageHeader, StatusBadge } from "@/components/ui";
import {
  adminAuditLogs,
  adminFeatures,
  adminSetFeature,
  adminUpdateUser,
  adminUsers,
  formatWhen,
  type AdminUserRow,
  type AuditLogEntry,
  type FeatureFlag,
} from "@/lib/api";

export default function AdminPage() {
  const [features, setFeatures] = useState<FeatureFlag[] | null>(null);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    Promise.all([adminFeatures(), adminAuditLogs(50), adminUsers()])
      .then(([feats, logs, userRes]) => {
        setFeatures(feats);
        setAudit(logs.entries);
        setUsers(userRes.users ?? []);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load administration data"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggle(feature: FeatureFlag, enabled: boolean) {
    setBusy(feature.key);
    try {
      await adminSetFeature(feature.key, enabled);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update feature");
    } finally {
      setBusy("");
    }
  }

  async function setUserField(id: string, patch: { role?: string; status?: string }) {
    setBusy(`user:${id}`);
    try {
      await adminUpdateUser(id, patch);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update user");
    } finally {
      setBusy("");
    }
  }

  if (!features) return <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8"><Loader /></div>;

  const groups: Record<string, FeatureFlag[]> = {};
  for (const f of features) {
    (groups[f.group] ??= []).push(f);
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Administration"
        subtitle="Feature controls, user roles and audit trail."
      />

      {error && <div className="mb-6"><Err message={error} /></div>}

      <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Users">
          <p className="mb-4 text-xs text-gray-500">
            Manage roles and account status. Disabling an account blocks its sign-in;
            role determines access to admin and gated features.
          </p>
          {users.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">No users found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-xs text-gray-500">
                    <th className="py-2 pr-3 font-medium">User</th>
                    <th className="py-2 pr-3 font-medium">Role</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Last login</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-gray-900">
                      <td className="py-2 pr-3">
                        <p className="text-gray-200">
                          {u.name}
                          {u.username ? <span className="ml-1 text-xs text-gray-500">@{u.username}</span> : null}
                        </p>
                        <p className="text-xs text-gray-500">{u.email}</p>
                      </td>
                      <td className="py-2 pr-3">
                        <select
                          value={u.role}
                          disabled={busy === `user:${u.id}`}
                          onChange={(e) => setUserField(u.id, { role: e.target.value })}
                          className="rounded-lg border border-gray-700 bg-gray-950 px-2 py-1 text-xs text-gray-300 disabled:opacity-50"
                        >
                          <option value="user">user</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td className="py-2 pr-3">
                        {u.status === "active" ? (
                          <StatusBadge label="active" tone="green" />
                        ) : (
                          <StatusBadge label="disabled" tone="red" />
                        )}
                        <button
                          type="button"
                          disabled={busy === `user:${u.id}`}
                          onClick={() =>
                            setUserField(u.id, {
                              status: u.status === "active" ? "disabled" : "active",
                            })
                          }
                          className="ml-2 rounded border border-gray-700 px-2 py-0.5 text-[11px] text-gray-400 hover:bg-gray-800 disabled:opacity-50"
                        >
                          {u.status === "active" ? "disable" : "enable"}
                        </button>
                      </td>
                      <td className="py-2 text-xs text-gray-500">
                        {formatWhen(u.last_login)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Rights & access">
          <p className="mb-4 text-xs text-gray-500">
            Every feature is enforced by the backend before its route runs. These controls mirror the
            feature table and update menu visibility plus endpoint access together.
          </p>
          <div className="flex flex-col gap-3">
            {Object.entries(groups).map(([group, feats]) => (
              <div key={group}>
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
                  {group}
                </p>
                <div className="flex flex-col gap-1.5">
                    {feats.map((f) => (
                    <div
                      key={f.key}
                      className="flex items-center justify-between gap-4 rounded-lg border border-gray-800 bg-gray-950 px-3 py-2.5 text-left text-sm"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-gray-200">{f.label}</p>
                        <p className="mt-0.5 text-[10px] text-gray-600">{f.key} · roles: {f.roles}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                          f.enabled
                            ? "border-emerald-700 bg-emerald-500/15 text-emerald-300"
                            : "border-gray-700 bg-gray-800 text-gray-400"
                          }`}
                        >{f.enabled ? "ON" : "OFF"}</span>
                        <button
                          type="button"
                          disabled={busy === f.key}
                          onClick={() => toggle(f, !f.enabled)}
                          className="rounded border border-gray-700 px-2 py-1 text-[11px] text-gray-300 hover:bg-gray-800 disabled:opacity-50"
                        >
                          {busy === f.key ? "Saving…" : f.enabled ? "Disable" : "Enable"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Audit Log">
          <p className="mb-4 text-xs text-gray-500">
            Who did what, when — login, feature changes and admin actions.
          </p>
          {audit.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">No recorded activity.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {audit.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-gray-800 bg-gray-950 px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-gray-200">{entry.action}</p>
                    <p className="truncate text-xs text-gray-500">
                      by {entry.user}
                      {entry.target ? ` → ${entry.target}` : ""}
                      {entry.detail ? ` · ${entry.detail}` : ""}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-gray-600">
                    {formatWhen(entry.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
    </div>
  );
}