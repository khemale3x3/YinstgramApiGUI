"use client";

import { useCallback, useEffect, useState } from "react";
import { Btn, Card, Err, Empty, Loader, PageHeader, Pagination, ProgressBar, StatusBadge } from "@/components/ui";
import {
  cancelJob,
  createJob,
  deleteJob,
  listJobs,
  listProjects,
  retryJob,
  formatWhen,
  type Job,
  type JobKind,
} from "@/lib/api";

const KINDS: JobKind[] = ["scrape", "analyze", "export", "full", "index", "ingest", "s3_upload"];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const [kind, setKind] = useState<JobKind>("scrape");
  const [project, setProject] = useState("");
  const [source, setSource] = useState("");
  const [prefix, setPrefix] = useState("");
  const [withGender, setWithGender] = useState(true);
  const [withCsv, setWithCsv] = useState(true);
  const [withJpg, setWithJpg] = useState(true);
  const [testLimit, setTestLimit] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const refresh = useCallback(async () => {
    try {
      const data = await listJobs(200);
      setJobs(data.jobs);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    listJobs(200)
      .then((data) => {
        setJobs(data.jobs);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load jobs"))
      .finally(() => setLoading(false));
    listProjects()
      .then((p) => setProjects(p.projects.map((pr) => pr.name)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 2500);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await createJob({
        kind,
        project: project || null,
        source: source || null,
        s3_prefix: prefix || null,
        with_gender: withGender,
        with_csv: withCsv,
        with_jpg: withJpg,
        test_limit: testLimit ? Number(testLimit) : null,
      });
      setSource("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start job");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(id: string) {
    await cancelJob(id);
    await refresh();
  }

  async function handleRetry(id: string) {
    try {
      await retryJob(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    }
  }

  async function handleDelete(id: string) {
    await deleteJob(id);
    await refresh();
  }

  const byStatus = (status: Job["status"]) =>
    jobs.filter((j) => j.status === status).length;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Jobs" subtitle="Background pipeline, ingest and storage tasks with live progress." />

      {error && <div className="mb-6"><Err message={error} /></div>}

      <Card title="Start a job" className="mb-8">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-gray-400">Kind</span>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as JobKind)}
              className={`w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600 ${kind === "s3_upload" ? "" : ""}`}
            >
              {KINDS.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </label>

          {!["ingest", "s3_upload"].includes(kind) ? (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-400">Project</span>
              <select
                value={project}
                onChange={(e) => setProject(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600"
              >
                <option value="">— select project —</option>
                {projects.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </label>
          ) : null}

          {["ingest", "s3_upload"].includes(kind) && (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-400">
                {kind === "ingest" ? "Keylist path" : "Local path"}
              </span>
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder={kind === "ingest" ? "/abs/path/keylist.jsonl" : "/abs/path/folder"}
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
              />
            </label>
          )}

          {kind === "s3_upload" && (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-400">S3 prefix</span>
              <input
                value={prefix}
                onChange={(e) => setPrefix(e.target.value)}
                placeholder="projects/demo"
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
              />
            </label>
          )}

          {["scrape", "analyze", "export", "full"].includes(kind) && (
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-400">Test limit (optional)</span>
              <input
                value={testLimit}
                onChange={(e) => setTestLimit(e.target.value)}
                type="number"
                placeholder="e.g. 10"
                className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
              />
            </label>
          )}

          {["analyze", "full"].includes(kind) && (
            <div className="flex flex-wrap items-end gap-4">
              <Toggle label="Gender/logo detection" checked={withGender} onChange={setWithGender} />
              <Toggle label="CSV" checked={withCsv} onChange={setWithCsv} />
              <Toggle label="JPGs" checked={withJpg} onChange={setWithJpg} />
            </div>
          )}

          <div className="flex items-end">
            <Btn primary type="submit" disabled={submitting} className="w-full">
              {submitting ? "Starting…" : "Start job"}
            </Btn>
          </div>
        </form>
      </Card>

      {loading ? (
        <Loader />
      ) : jobs.length === 0 ? (
        <Empty label="No jobs yet." />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <Legend label="Running" count={byStatus("running")} color="bg-amber-400" />
            <Legend label="Queued" count={byStatus("queued")} color="bg-gray-400" />
            <Legend label="Completed" count={byStatus("succeeded")} color="bg-emerald-500" />
            <Legend label="Failed" count={byStatus("failed")} color="bg-red-500" />
            <Legend label="Cancelled" count={byStatus("cancelled")} color="bg-blue-400" />
          </div>
          <div className="space-y-3">
          {jobs.slice((page - 1) * pageSize, page * pageSize).map((job) => (
            <div key={job.id} className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-gray-500">{job.id}</span>
                  <span className="text-sm font-semibold text-white capitalize">{job.kind}</span>
                  {job.project ? (
                    <span className="text-sm text-gray-400">Output_{job.project}</span>
                  ) : null}
                  <StatusBadge label={job.status} tone={toneFor(job.status)} />
                </div>
                <div className="flex items-center gap-2">
                  {job.current_step && job.status === "running" ? (
                    <span className="text-xs text-amber-300">{job.current_step}</span>
                  ) : null}
                  <Btn size="sm" onClick={() => setExpanded(expanded === job.id ? null : job.id)}>
                    {expanded === job.id ? "Hide" : "Details"}
                  </Btn>
                  {["running", "queued"].includes(job.status) && (
                    <Btn size="sm" danger onClick={() => handleCancel(job.id)}>Cancel</Btn>
                  )}
                  {["failed", "cancelled"].includes(job.status) && (
                    <Btn size="sm" onClick={() => handleRetry(job.id)}>Retry</Btn>
                  )}
                  {["succeeded", "failed", "cancelled"].includes(job.status) && (
                    <Btn size="sm" onClick={() => handleDelete(job.id)}>Delete</Btn>
                  )}
                </div>
              </div>

              <div className="mt-3 flex items-center gap-3">
                <ProgressBar value={job.progress} />
                <span className="text-xs text-gray-500">{Math.round(job.progress)}%</span>
              </div>

              <p className="mt-2 text-xs text-gray-600">created {formatWhen(job.created_at)}</p>

              {expanded === job.id && (
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  {job.error ? (
                    <div className="rounded-lg border border-red-900 bg-red-950/50 p-3 text-xs text-red-300">
                      {job.error}
                    </div>
                  ) : null}
                  {job.result && Object.keys(job.result).length > 0 ? (
                    <pre className="overflow-x-auto rounded-lg border border-gray-800 bg-gray-950 p-3 text-xs text-gray-300">
                      {JSON.stringify(job.result, null, 2)}
                    </pre>
                  ) : null}
                  <div className="max-h-48 overflow-y-auto rounded-lg border border-gray-800 bg-gray-950 p-3 text-xs text-gray-400">
                    {(job.log ?? []).map((line, i) => (
                      <p key={i} className="py-0.5">{line}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          </div>
          <Pagination page={page} pageSize={pageSize} total={jobs.length} onPage={setPage} />
        </>
      )}
    </div>
  );
}

function toneFor(status: Job["status"]): "green" | "amber" | "red" | "gray" {
  switch (status) {
    case "running":
    case "queued":
      return "amber";
    case "succeeded":
      return "green";
    case "failed":
      return "red";
    default:
      return "gray";
  }
}

function Legend({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      <span className="text-gray-400">{label}</span>
      <span className="font-semibold text-white">{count}</span>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer pb-2.5">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="accent-white" />
      <span className="text-xs text-gray-300">{label}</span>
    </label>
  );
}