"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  deleteCampaign,
  formatNumber,
  formatWhen,
  getCampaign,
  sendCampaignRequest,
  setCampaignRequestStatus,
  updateCampaign,
  type CampaignCreatorRow,
  type CampaignDetail,
  type CampaignRequestRow,
} from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-300 border-emerald-700",
  matched: "bg-blue-500/15 text-blue-300 border-blue-700",
  draft: "bg-amber-500/15 text-amber-300 border-amber-700",
  completed: "bg-gray-500/15 text-gray-300 border-gray-600",
  cancelled: "bg-red-500/15 text-red-300 border-red-700",
};

export default function CampaignDetailPage() {
  const params = useParams<{ campaignId: string }>();
  const id = (params?.campaignId ?? "").toString();

  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!id) return;
    let alive = true;
    getCampaign(id)
      .then((d) => {
        if (!alive) return;
        const c = d.campaign;
        setCampaign(c);
        setForm({
          name: c.name,
          budget_min: String(c.budget_min),
          budget_max: String(c.budget_max),
          target_count: String(c.target_count),
          location: c.location,
          audience: c.audience,
          min_engagement: String(c.min_engagement),
          notes: c.notes,
        });
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load campaign"));
    return () => {
      alive = false;
    };
  }, [id]);

  async function save() {
    if (!campaign) return;
    setBusy(true);
    setError("");
    try {
      const updated = await updateCampaign(campaign.id, {
        name: form.name,
        budget_min: Number(form.budget_min) || 0,
        budget_max: Number(form.budget_max) || 0,
        target_count: Number(form.target_count) || 10,
        location: form.location,
        audience: form.audience,
        min_engagement: Number(form.min_engagement) || 0,
        notes: form.notes,
      });
      setCampaign({ ...updated.campaign, creators: campaign.creators, requests: campaign.requests });
      setMessage("Campaign updated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!campaign) return;
    if (!window.confirm(`Delete campaign "${campaign.name}"?`)) return;
    setBusy(true);
    try {
      await deleteCampaign(campaign.id);
      setDeleted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
      setBusy(false);
    }
  }

  async function request(creator: CampaignCreatorRow) {
    if (!campaign) return;
    setBusy(true);
    setError("");
    try {
      await sendCampaignRequest(campaign.id, creator.creator_username, message);
      const d = await getCampaign(campaign.id);
      setCampaign(d.campaign);
      setMessage(`Request queued for @${creator.creator_username}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function updateRequestStatus(creator: string, status: string) {
    if (!campaign) return;
    try {
      await setCampaignRequestStatus(campaign.id, creator, status);
      const d = await getCampaign(campaign.id);
      setCampaign(d.campaign);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  if (deleted) {
    return (
      <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-10 text-center">
          <p className="text-sm text-gray-300">Campaign deleted.</p>
          <Link href="/campaigns" className="mt-4 inline-block text-xs text-blue-400 hover:underline">
            Back to campaigns →
          </Link>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold tracking-tight text-white">Campaign</h1>
        {error ? (
          <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>
        ) : (
          <p className="mt-4 text-sm text-gray-500">Loading…</p>
        )}
      </div>
    );
  }

  const { creators, requests } = campaign;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">{campaign.name}</h1>
          <p className="mt-1 text-sm text-gray-400">
            {campaign.location || "any location"} · {campaign.audience || "broad audience"} · created {formatWhen(campaign.created_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className={`rounded-full border px-2.5 py-1 text-xs ${STATUS_COLORS[campaign.status] ?? STATUS_COLORS.draft}`}>
            {campaign.status}
          </span>
          <Link
            href={`/campaigns/${campaign.id}/matching`}
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black"
          >
            Run matching
          </Link>
          <button onClick={remove} disabled={busy} className="rounded-lg border border-red-900 px-4 py-2 text-sm text-red-300 hover:bg-red-950/50 disabled:opacity-50">
            Delete
          </button>
        </div>
      </div>

      {message && (
        <div className="mt-4 rounded-lg border border-emerald-900 bg-emerald-950/50 p-4 text-sm text-emerald-300">{message}</div>
      )}
      {error && (
        <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>
      )}

      <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Brief</h2>
          <button onClick={save} disabled={busy} className="rounded-lg bg-gray-100 px-4 py-1.5 text-sm font-medium text-black disabled:opacity-50">
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <BriefField label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <BriefField label="Budget min ($)" value={form.budget_min} onChange={(v) => setForm({ ...form, budget_min: v })} />
          <BriefField label="Budget max ($)" value={form.budget_max} onChange={(v) => setForm({ ...form, budget_max: v })} />
          <BriefField label="Target creators" value={form.target_count} onChange={(v) => setForm({ ...form, target_count: v })} />
          <BriefField label="Location" value={form.location} onChange={(v) => setForm({ ...form, location: v })} />
          <BriefField label="Audience keywords" value={form.audience} onChange={(v) => setForm({ ...form, audience: v })} />
          <BriefField label="Min engagement" value={form.min_engagement} onChange={(v) => setForm({ ...form, min_engagement: v })} />
          <div className="md:col-span-2 lg:col-span-4">
            <BriefField label="Notes" value={form.notes} onChange={(v) => setForm({ ...form, notes: v })} />
          </div>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-200">Matched creators ({creators.length})</h2>
            <Link href={`/campaigns/${campaign.id}/matching`} className="text-xs text-blue-400 hover:underline">
              Rerun matching →
            </Link>
          </div>
          {creators.length === 0 ? (
            <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-8 text-center">
              <p className="text-sm text-gray-500">
                No matches yet. Run matching to score saved profiles against this brief.
              </p>
              <Link
                href={`/campaigns/${campaign.id}/matching`}
                className="mt-4 inline-block rounded-lg bg-white px-4 py-2 text-sm font-medium text-black"
              >
                Open matching
              </Link>
            </div>
          ) : (
            <div className="mt-4 flex flex-col gap-2">
              {creators.map((c) => (
                <div key={c.id} className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <Link href={`/creators/${c.creator_username}`} className="min-w-0">
                      <p className="truncate text-sm font-medium text-white">#{c.rank} @{c.creator_username}</p>
                      <p className="truncate text-xs text-gray-500">
                        {c.full_name || "—"}
                        {c.category ? ` · ${c.category}` : ""}
                      </p>
                    </Link>
                    <span className="shrink-0 rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-semibold text-white">
                      {Math.round(c.score)}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <span>{formatNumber(c.followers)} followers</span>
                    {c.location ? <span>· {c.location}</span> : null}
                    <span className="ml-auto text-gray-600">{c.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h2 className="text-sm font-semibold text-gray-200">Requests ({requests.length})</h2>
          <div className="mt-4 flex gap-2">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Default outreach message (±)"
              className="flex-1 rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
            />
            <span className="self-center rounded-lg border border-gray-800 px-3 py-2 text-xs text-gray-500">
              send via creator row
            </span>
          </div>
          {requests.length === 0 ? (
            <p className="mt-6 text-sm text-gray-500">
              Send an outreach request from a matched creator&apos;s panel (to the right).
            </p>
          ) : (
            <div className="mt-4 flex flex-col gap-2">
              {requests.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-3 rounded-lg border border-gray-800 bg-gray-950 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">@{r.creator_username}</p>
                    <p className="truncate text-xs text-gray-500">{formatWhen(r.created_at)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {["pending", "sent", "accepted", "declined"].map((s) => (
                      <button
                        key={s}
                        onClick={() => updateRequestStatus(r.creator_username, s)}
                        className={`rounded-full border px-2 py-0.5 text-xs ${
                          r.status === s
                            ? "border-white bg-white text-black"
                            : "border-gray-700 text-gray-400 hover:text-white"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {creators.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-gray-500">Send request to:</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {creators.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => request(c)}
                    disabled={busy}
                    className="rounded-full border border-gray-700 px-3 py-1 text-xs text-gray-300 hover:bg-gray-900 disabled:opacity-50"
                  >
                    @{c.creator_username}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function BriefField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600"
      />
    </label>
  );
}

export type { CampaignCreatorRow, CampaignRequestRow };