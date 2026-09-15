"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import {
  createCampaign,
  formatNumber,
  formatWhen,
  getCampaign,
  listCampaigns,
  recentProfiles,
  type Campaign,
  type CampaignDetail,
  type CampaignRequestRow,
} from "@/lib/api";

type Tab = "all" | "requests" | "matching" | "recommendations";

const TABS: Array<{ key: Tab; label: string }> = [
  { key: "all", label: "Campaigns" },
  { key: "requests", label: "Requests" },
  { key: "matching", label: "Matching" },
  { key: "recommendations", label: "Recommendations" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-300 border-emerald-700",
  matched: "bg-blue-500/15 text-blue-300 border-blue-700",
  draft: "bg-amber-500/15 text-amber-300 border-amber-700",
  completed: "bg-gray-500/15 text-gray-300 border-gray-600",
  cancelled: "bg-red-500/15 text-red-300 border-red-700",
};

export default function CampaignsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [refreshKey, setRefreshKey] = useState(0);
  const children: Record<Tab, ReactNode> = {
    all: <CampaignList refreshKey={refreshKey} onChanged={() => setRefreshKey((k) => k + 1)} />,
    requests: <RequestsView refreshKey={refreshKey} />,
    matching: <MatchingPicker />,
    recommendations: <Recommendations />,
  };

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Campaigns</h1>
          <p className="mt-1 text-sm text-gray-400">
            Briefs, creator matching and outreach requests.
          </p>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap gap-2 border-b border-gray-800 pb-px">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={
              tab === t.key
                ? "rounded-t-lg border-b-2 border-white px-3 py-2 text-sm font-medium text-white"
                : "rounded-t-lg border-b-2 border-transparent px-3 py-2 text-sm text-gray-500 hover:text-gray-300"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">{children[tab]}</div>
    </div>
  );
}

function CampaignList({
  refreshKey,
  onChanged,
}: {
  refreshKey: number;
  onChanged: () => void;
}) {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    budget_min: "",
    budget_max: "",
    target_count: "10",
    location: "",
    audience: "",
    min_engagement: "",
    notes: "",
  });

  useEffect(() => {
    let alive = true;
    listCampaigns()
      .then((d) => alive && setCampaigns(d.campaigns))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load campaigns"));
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  async function create() {
    if (!form.name.trim()) return;
    setSaving(true);
    setError("");
    try {
      await createCampaign({
        name: form.name,
        budget_min: Number(form.budget_min) || 0,
        budget_max: Number(form.budget_max) || 0,
        target_count: Number(form.target_count) || 10,
        location: form.location,
        audience: form.audience,
        min_engagement: Number(form.min_engagement) || 0,
        notes: form.notes,
      });
      setForm({
        name: "", budget_min: "", budget_max: "", target_count: "10",
        location: "", audience: "", min_engagement: "", notes: "",
      });
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <h2 className="text-sm font-semibold text-gray-200">All campaigns</h2>
        {error && (
          <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>
        )}
        {campaigns === null ? (
          <p className="mt-6 text-sm text-gray-500">Loading…</p>
        ) : campaigns.length === 0 ? (
          <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
            <p className="text-sm text-gray-400">
              No campaigns yet. Define your first brief to start matching creators.
            </p>
          </div>
        ) : (
          <div className="mt-6 flex flex-col gap-2">
            {campaigns.map((c) => (
              <Link
                key={c.id}
                href={`/campaigns/${c.id}`}
                className="flex items-center justify-between gap-4 rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 hover:border-gray-700"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{c.name}</p>
                  <p className="mt-0.5 truncate text-xs text-gray-500">
                    {c.location || "any location"} · {c.audience || "broad audience"} ·{" "}
                    {c.budget_min > 0 ? `$${c.budget_min.toLocaleString()}+` : "open budget"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3 text-right">
                  <span className="text-xs text-gray-500">{c.matched ?? 0} matched</span>
                  <span className={`rounded-full border px-2.5 py-0.5 text-xs ${STATUS_COLORS[c.status] ?? STATUS_COLORS.draft}`}>
                    {c.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5 lg:sticky lg:top-8 self-start">
        <h2 className="text-sm font-semibold text-gray-200">New campaign</h2>
        <div className="mt-4 flex flex-col gap-3">
          <Field
            label="Name *"
            value={form.name}
            onChange={(v) => setForm({ ...form, name: v })}
            placeholder="e.g. Summer launch"
          />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Budget min ($)"
              value={form.budget_min}
              onChange={(v) => setForm({ ...form, budget_min: v })}
              placeholder="0"
            />
            <Field
              label="Max"
              value={form.budget_max}
              onChange={(v) => setForm({ ...form, budget_max: v })}
              placeholder="0"
            />
          </div>
          <Field
            label="Target count"
            value={form.target_count}
            onChange={(v) => setForm({ ...form, target_count: v })}
            placeholder="10"
          />
          <Field
            label="Location"
            value={form.location}
            onChange={(v) => setForm({ ...form, location: v })}
            placeholder="e.g. London"
          />
          <Field
            label="Audience keywords"
            value={form.audience}
            onChange={(v) => setForm({ ...form, audience: v })}
            placeholder="fitness, gym, wellness"
          />
          <Field
            label="Min engagement (0–1)"
            value={form.min_engagement}
            onChange={(v) => setForm({ ...form, min_engagement: v })}
            placeholder="0.02"
          />
          <Field
            label="Notes"
            value={form.notes}
            onChange={(v) => setForm({ ...form, notes: v })}
            placeholder="KPI notes…"
          />
          <button
            onClick={create}
            disabled={saving || !form.name.trim()}
            className="mt-1 rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-black disabled:opacity-50"
          >
            {saving ? "Creating…" : "Create campaign"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
      />
    </label>
  );
}

function RequestsView({ refreshKey }: { refreshKey: number }) {
  const [requests, setRequests] = useState<Array<{ campaign: Campaign; request: CampaignRequestRow }> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    listCampaigns()
      .then(async (d) => {
        const filled: Array<{ campaign: Campaign; request: CampaignRequestRow }> = [];
        for (const c of d.campaigns.slice(0, 30)) {
          try {
            const detail = await getCampaign(c.id);
            for (const r of detail.campaign.requests ?? []) {
              filled.push({ campaign: c, request: r });
            }
          } catch {
            // skip campaigns that fail to load
          }
        }
        if (alive) setRequests(filled);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load requests"));
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-200">Outreach requests</h2>
      {error && <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>}
      {requests === null ? (
        <p className="mt-6 text-sm text-gray-500">Loading…</p>
      ) : requests.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
          <p className="text-sm text-gray-400">
            No requests sent yet. Match creators in a campaign and send outreach there.
          </p>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-2">
          {requests.map(({ campaign, request }, i) => (
            <Link
              key={i}
              href={`/campaigns/${campaign.id}`}
              className="flex items-center justify-between gap-4 rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 hover:border-gray-700"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white">@{request.creator_username}</p>
                <p className="truncate text-xs text-gray-500">
                  {campaign.name} · sent {formatWhen(request.created_at)}
                </p>
              </div>
              <span className="shrink-0 text-xs text-gray-400">{request.status}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function MatchingPicker() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    listCampaigns()
      .then((d) => alive && setCampaigns(d.campaigns))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load campaigns"));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-200">Matching</h2>
      <p className="mt-1 text-xs text-gray-500">
        Pick a campaign to run creator matching against the saved profile store.
      </p>
      {error && <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>}
      {campaigns.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
          <p className="text-sm text-gray-400">Create a campaign first to open its matching screen.</p>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-2">
          {campaigns.map((c) => (
            <Link
              key={c.id}
              href={`/campaigns/${c.id}/matching`}
              className="flex items-center justify-between rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 hover:border-gray-700"
            >
              <span className="text-sm font-medium text-white">{c.name}</span>
              <span className="text-xs text-gray-500">{c.matched ?? 0} matched →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Recommendations() {
  const [top, setTop] = useState<Array<{ username: string; followers: number; category: string }>>([]);

  useEffect(() => {
    let alive = true;
    recentProfiles(50)
      .then((d) => alive && setTop(d.results.map((p) => ({
        username: p.username,
        followers: p.followers,
        category: p.category ?? "",
      }))))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-200">Recommendations</h2>
      <p className="mt-1 text-xs text-gray-500">
        High-reach creators to shortlist for upcoming campaign briefs.
      </p>
      {top.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
          <p className="text-sm text-gray-400">No creators stored yet — recommendations appear once profiles are collected.</p>
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-2">
          {top.map((c) => (
            <Link
              key={c.username}
              href={`/creators/${c.username}`}
              className="flex items-center justify-between rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 hover:border-gray-700"
            >
              <span className="min-w-0 truncate text-sm font-medium text-white">
                @{c.username}
                {c.category ? <span className="text-gray-500"> · {c.category}</span> : null}
              </span>
              <span className="shrink-0 text-xs text-gray-500">{formatNumber(c.followers)}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export type { Tab as CampaignsTab };
export type { CampaignDetail };