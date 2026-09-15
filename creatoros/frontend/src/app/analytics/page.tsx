"use client";

import { useState } from "react";
import { instagramAction } from "@/lib/api";

export default function AnalyticsPage() {
  const [metric, setMetric] = useState("impressions,reach,follower_count");
  const [period, setPeriod] = useState("day");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError("");
    setResult("");
    try {
      const data = await instagramAction("insights", { metric, period });
      setResult(JSON.stringify(data, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Insights request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">Analytics</h1>
      <p className="mt-1 text-sm text-gray-400">Reach, impressions, follower demographics, and Instagram Graph API Insights.</p>
      <div className="mt-8 grid gap-6 lg:grid-cols-5">
        <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Instagram Graph API</p>
          <h2 className="mt-1 text-lg font-semibold text-white">Pull performance metrics</h2>
          <p className="mt-1 text-sm text-gray-500">Configure a Business or Creator account ID and access token in Settings before running Insights.</p>
          <label className="mt-5 block"><span className="mb-1 block text-xs font-medium text-gray-400">Metrics</span><input value={metric} onChange={(e) => setMetric(e.target.value)} className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white" /></label>
          <label className="mt-4 block"><span className="mb-1 block text-xs font-medium text-gray-400">Period</span><select value={period} onChange={(e) => setPeriod(e.target.value)} className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white"><option value="day">Day</option><option value="week">Week</option><option value="lifetime">Lifetime</option></select></label>
          <button type="button" onClick={() => void run()} disabled={busy} className="mt-5 rounded-lg bg-white px-4 py-3 text-sm font-medium text-black hover:bg-gray-200 disabled:opacity-50">{busy ? "Loading..." : "Pull analytics"}</button>
          {error && <p className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-3 text-sm text-red-300">{error}</p>}
        </section>
        <aside className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-2"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Result</p>{result ? <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-emerald-300">{result}</pre> : <p className="mt-4 text-sm text-gray-500">Graph API metrics and errors appear here.</p>}</aside>
      </div>
    </div>
  );
}
