"use client";

import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import { Err, Loader } from "@/components/ui";
import {
  formatWhen,
  trackingConnections,
  trackingStats,
  trackingTraffic,
  type ConnectionEntry,
  type TrafficEntry,
  type TrafficStats,
} from "@/lib/api";

export default function TrackingPage() {
  const [stats, setStats] = useState<TrafficStats | null>(null);
  const [traffic, setTraffic] = useState<TrafficEntry[]>([]);
  const [connections, setConnections] = useState<ConnectionEntry[]>([]);
  const [tab, setTab] = useState<"traffic" | "connections">("traffic");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    Promise.all([trackingStats(), trackingTraffic(200), trackingConnections(100)])
      .then(([s, t, c]) => {
        if (!alive) return;
        setStats(s);
        setTraffic(t.entries);
        setConnections(c.entries);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load tracking"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const statusTone = (code: number) =>
    code < 300 ? "text-emerald-400" : code < 500 ? "text-amber-400" : "text-red-400";

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">Tracking</h1>
      <p className="mt-1 text-sm text-gray-400">
        Every API call and sign-in, recorded with IP, device and location. Admin only.
      </p>

      {error && <div className="mt-6"><Err message={error} /></div>}

      {!stats ? (
        loading ? (
          <Loader />
        ) : null
      ) : (
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard title="API Requests" value={String(stats.requests)} />
          <StatCard title="Avg Latency" value={`${stats.avg_duration_ms} ms`} />
          <StatCard title="Connections" value={String(stats.connections)} />
          <StatCard title="Total Time" value={`${Math.round(stats.duration_ms / 1000)} s`} />
        </div>
      )}

      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats
          ? Object.entries(stats.by_status)
              .sort((a, b) => Number(a[0]) - Number(b[0]))
              .map(([code, count]) => (
                <div
                  key={code}
                  className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 text-sm"
                >
                  <span className={`font-semibold ${statusTone(Number(code))}`}>{code}</span>
                  <span className="text-gray-400"> — {count} requests</span>
                </div>
              ))
          : null}
      </div>

      <div className="mt-8 flex gap-4 border-b border-gray-800">
        <button
          onClick={() => setTab("traffic")}
          className={
            tab === "traffic"
              ? "border-b-2 border-white px-3 py-2 text-sm font-medium text-white"
              : "border-b-2 border-transparent px-3 py-2 text-sm text-gray-500 hover:text-gray-300"
          }
        >
          API Traffic
        </button>
        <button
          onClick={() => setTab("connections")}
          className={
            tab === "connections"
              ? "border-b-2 border-white px-3 py-2 text-sm font-medium text-white"
              : "border-b-2 border-transparent px-3 py-2 text-sm text-gray-500 hover:text-gray-300"
          }
        >
          Connections
        </button>
      </div>

      {tab === "traffic" ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-gray-800 bg-gray-900/50">
          {traffic.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">No API traffic recorded yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">User</th>
                  <th className="px-4 py-2.5 font-medium">Method</th>
                  <th className="px-4 py-2.5 font-medium">Path</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Latency</th>
                  <th className="px-4 py-2.5 font-medium">Client</th>
                </tr>
              </thead>
              <tbody>
                {traffic.map((e) => (
                  <tr key={e.id} className="border-b border-gray-800/60">
                    <td className="px-4 py-2 text-xs text-gray-500">{formatWhen(e.created_at)}</td>
                    <td className="px-4 py-2 text-gray-300">{e.user || e.email || "anonymous"}</td>
                    <td className="px-4 py-2 text-gray-300">{e.method}</td>
                    <td className="max-w-[240px] truncate px-4 py-2 text-gray-400">{e.path}</td>
                    <td className={`px-4 py-2 font-medium ${statusTone(e.status_code)}`}>{e.status_code}</td>
                    <td className="px-4 py-2 text-gray-500">{e.duration_ms} ms</td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {e.browser}{e.os ? ` / ${e.os}` : ""}
                      {e.ip ? ` · ${e.ip.slice(0, 24)}` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-xl border border-gray-800 bg-gray-900/50">
          {connections.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">No connections recorded yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">User</th>
                  <th className="px-4 py-2.5 font-medium">Event</th>
                  <th className="px-4 py-2.5 font-medium">Device</th>
                  <th className="px-4 py-2.5 font-medium">Browser</th>
                  <th className="px-4 py-2.5 font-medium">OS</th>
                  <th className="px-4 py-2.5 font-medium">Location</th>
                  <th className="px-4 py-2.5 font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((e) => (
                  <tr key={e.id} className="border-b border-gray-800/60">
                    <td className="px-4 py-2 text-xs text-gray-500">{formatWhen(e.created_at)}</td>
                    <td className="px-4 py-2 text-gray-300">{e.user}</td>
                    <td className="px-4 py-2 text-gray-400">{e.event}</td>
                    <td className="px-4 py-2 text-gray-400">{e.device}</td>
                    <td className="px-4 py-2 text-gray-400">{e.browser}</td>
                    <td className="px-4 py-2 text-gray-400">{e.os}</td>
                    <td className="px-4 py-2 text-gray-400">{e.location || "—"}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{e.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}