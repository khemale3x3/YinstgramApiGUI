"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import { Err, Loader, ProgressBar, StatusBadge } from "@/components/ui";
import {
  formatWhen,
  getSessions,
  listJobs,
  type Job,
  type SessionCounts,
} from "@/lib/api";

const EMPTY_SESSIONS: SessionCounts = {
  cookie_total: 0,
  cookie_active: 0,
  cookie_backup: 0,
  instagrapi: 0,
  total: 0,
};

export default function MonitoringPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sessions, setSessions] = useState<SessionCounts>(EMPTY_SESSIONS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    Promise.all([listJobs(30), getSessions()])
      .then(([jobsRes, sess]) => {
        if (!alive) return;
        setJobs(jobsRes.jobs);
        setSessions(sess.counts);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const running = jobs.filter((j) => j.status === "running").length;
  const queued = jobs.filter((j) => j.status === "queued" || j.status === "pending").length;
  const failed = jobs.filter((j) => j.status === "failed").length;
  const succeeded = jobs.filter((j) => j.status === "succeeded").length;

  const toneMap: Record<string, "gray" | "green" | "amber" | "red"> = {
    running: "amber",
    queued: "amber",
    pending: "amber",
    succeeded: "green",
    failed: "red",
    cancelled: "gray",
  };

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">Monitoring</h1>
      <p className="mt-1 text-sm text-gray-400">
        Live view of background jobs, workers and account session health.
      </p>

      {error && <div className="mt-6"><Err message={error} /></div>}

      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Running" value={String(running)} />
        <StatCard title="Queued" value={String(queued)} />
        <StatCard title="Succeeded" value={String(succeeded)} />
        <StatCard title="Failed" value={String(failed)} />
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h2 className="mb-2 text-sm font-semibold text-gray-200">Session Health</h2>
          <p className="text-xs text-gray-500">Cookie sessions loaded from the session store.</p>
          <div className="mt-4 flex flex-col gap-2 text-sm">
            <HealthRow label="Active cookies" value={sessions.cookie_active} total={sessions.cookie_active + sessions.cookie_backup} />
            <HealthRow label="Backup cookies" value={sessions.cookie_backup} total={Math.max(1, sessions.cookie_total)} />
            <HealthRow label="Instagrapi" value={sessions.instagrapi} total={Math.max(1, sessions.instagrapi)} />
          </div>
          <Link
            href="/sessions"
            className="mt-4 inline-block text-xs text-blue-400 hover:underline"
          >
            Manage sessions →
          </Link>
        </div>

        <div className="md:col-span-2 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h2 className="mb-4 text-sm font-semibold text-gray-200">Running & Queued</h2>
          {loading ? (
            <Loader />
          ) : jobs.filter((j) => j.status === "running" || j.status === "queued" || j.status === "pending").length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">No active jobs.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {jobs
                .filter((j) => j.status === "running" || j.status === "queued" || j.status === "pending")
                .map((job) => (
                  <Link
                    key={job.id}
                    href="/jobs"
                    className="block rounded-lg border border-gray-800 bg-gray-950 p-4"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">
                          {job.kind}
                          {job.project ? ` · ${job.project}` : ""}
                        </p>
                        <p className="mt-0.5 text-xs text-gray-500">
                          {job.current_step} · started {formatWhen(job.created_at)}
                        </p>
                      </div>
                      <StatusBadge label={job.status} tone={toneMap[job.status] ?? "gray"} />
                    </div>
                    <div className="mt-3">
                      <ProgressBar value={job.progress} />
                    </div>
                  </Link>
                ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Recent Jobs</h2>
          <Link href="/jobs" className="text-xs text-blue-400 hover:underline">
            Open Jobs →
          </Link>
        </div>
        {loading ? (
          <Loader />
        ) : jobs.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-500">No jobs yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="pb-2 pr-4 font-medium">Kind</th>
                  <th className="pb-2 pr-4 font-medium">Project</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 pr-4 font-medium">Progress</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 15).map((job) => (
                  <tr key={job.id} className="border-b border-gray-800/60">
                    <td className="py-2.5 pr-4 text-gray-200">{job.kind}</td>
                    <td className="py-2.5 pr-4 text-gray-400">{job.project ?? "—"}</td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge label={job.status} tone={toneMap[job.status] ?? "gray"} />
                    </td>
                    <td className="py-2.5 pr-4 text-gray-400">{job.progress}%</td>
                    <td className="py-2.5 text-gray-500">{formatWhen(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function HealthRow({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="font-medium text-white">
        {value} <span className="text-xs text-gray-500">({pct}%)</span>
      </span>
    </div>
  );
}