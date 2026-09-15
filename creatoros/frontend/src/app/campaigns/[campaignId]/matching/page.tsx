"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  formatNumber,
  getCampaign,
  listCampaigns,
  matchCampaign,
  setCampaignCreatorStatus,
  type Campaign,
  type CampaignCreatorRow,
  type CampaignDetail,
} from "@/lib/api";

const MATCH_COLORS: Record<string, string> = {
  matched: "border-blue-700 bg-blue-500/15 text-blue-300",
  shortlisted: "border-amber-700 bg-amber-500/15 text-amber-300",
  added: "border-emerald-700 bg-emerald-500/15 text-emerald-300",
  accepted: "border-emerald-700 bg-emerald-500/15 text-emerald-300",
  requested: "border-violet-700 bg-violet-500/15 text-violet-300",
  declined: "border-red-700 bg-red-500/15 text-red-300",
};

export default function MatchingPage() {
  const params = useParams<{ campaignId: string }>();
  const id = (params?.campaignId ?? "").toString();

  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [fallback, setFallback] = useState<Campaign | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!id) return;
    let alive = true;
    getCampaign(id)
      .then((d) => alive && setCampaign(d.campaign))
      .catch(() => {});
    listCampaigns()
      .then((d) => {
        const match = d.campaigns.find((c) => c.id === id);
        if (alive && match) setFallback(match);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [id]);

  async function run() {
    setRunning(true);
    setError("");
    setMessage("");
    try {
      const result = await matchCampaign(id);
      const d = await getCampaign(id);
      setCampaign(d.campaign);
      setMessage(
        result.matched === 0
          ? "No saved creators matched this brief yet — collect creators first."
          : `Matched ${result.matched} creators against the brief.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Matching failed");
    } finally {
      setRunning(false);
    }
  }

  async function setStatus(creator: CampaignCreatorRow, status: string) {
    try {
      await setCampaignCreatorStatus(id, creator.creator_username, status);
      const d = await getCampaign(id);
      setCampaign(d.campaign);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  const name = campaign?.name ?? fallback?.name ?? id;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href={`/campaigns/${id}`} className="text-xs text-blue-400 hover:underline">
            ← Back to campaign
          </Link>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">Matching — {name}</h1>
          <p className="mt-1 text-sm text-gray-400">
            Score saved creators against the brief&apos;s audience, budget, engagement and location.
          </p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="shrink-0 rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black disabled:opacity-50"
        >
          {running ? "Matching…" : "Run matching"}
        </button>
      </div>

      {message && (
        <div className="mt-4 rounded-lg border border-emerald-900 bg-emerald-950/50 p-4 text-sm text-emerald-300">{message}</div>
      )}
      {error && (
        <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>
      )}

      {!campaign && !fallback && (
        <p className="mt-6 text-sm text-gray-500">Loading…</p>
      )}

      {campaign && (
        <>
          <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <h2 className="text-sm font-semibold text-gray-200">Scope</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-400">
              <span className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1">
                {campaign.location || "any location"}
              </span>
              <span className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1">
                {campaign.audience || "broad audience"}
              </span>
              {campaign.budget_min > 0 && (
                <span className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1">
                  ${campaign.budget_min.toLocaleString()}+ budget
                </span>
              )}
              {campaign.min_engagement > 0 && (
                <span className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1">
                  &gt;{Math.round(campaign.min_engagement * 100)}% engagement
                </span>
              )}
              <span className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1">
                top {campaign.target_count}
              </span>
            </div>
          </div>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-gray-200">
              Ranked matches ({campaign.creators.length})
            </h2>
            {campaign.creators.length === 0 ? (
              <div className="mt-4 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
                <p className="text-sm text-gray-500">
                  No matches cached yet — press Run matching to score the saved profile store.
                </p>
              </div>
            ) : (
              <div className="mt-4 flex flex-col gap-2">
                {campaign.creators.map((c) => (
                  <div
                    key={c.id}
                    className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <Link href={`/creators/${c.creator_username}`} className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-white">
                          #{c.rank}{" "}
                          <span className="text-base">@{c.creator_username}</span>
                          <span className="ml-2 text-xs text-gray-500">
                            {c.full_name || "—"}
                            {c.category ? ` · ${c.category}` : ""}
                          </span>
                        </p>
                        <p className="mt-0.5 truncate text-xs text-gray-500">
                          {formatNumber(c.followers)} followers
                          {c.location ? ` · ${c.location}` : ""}
                          {c.biography ? ` · ${c.biography}` : ""}
                        </p>
                      </Link>
                      <div className="flex shrink-0 items-center gap-3">
                        <span className="text-right">
                          <span className="block text-lg font-bold text-white">
                            {Math.round(c.score)}
                          </span>
                          <span className="block text-[11px] text-gray-500">match</span>
                        </span>
                        <span className={`rounded-full border px-2.5 py-1 text-xs ${MATCH_COLORS[c.status] ?? MATCH_COLORS.matched}`}>
                          {c.status}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {["shortlisted", "added", "requested", "accepted", "declined"].map((s) => (
                        <button
                          key={s}
                          onClick={() => setStatus(c, s)}
                          className={`rounded-full border px-2.5 py-1 text-xs ${
                            c.status === s
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
          </div>
        </>
      )}
    </div>
  );
}