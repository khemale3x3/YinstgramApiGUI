"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Btn, Card, Empty, Err, Input, PageHeader, Loader, StatusBadge } from "@/components/ui";
import {
  addProjectUrls,
  createJob,
  createProject,
  deleteProject,
  getProjectUrls,
  listProjects,
  removeProjectUrls,
  requeueFailedUrls,
  uploadProjectUrlsCsv,
  type JobKind,
  type Project,
  type ProjectUrls,
} from "@/lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");

  const [selected, setSelected] = useState<Project | null>(null);
  const [urls, setUrls] = useState<ProjectUrls | null>(null);
  const [addText, setAddText] = useState("");
  const [s3Prefix, setS3Prefix] = useState("");
  const [selectedUrls, setSelectedUrls] = useState<string[]>([]);

  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(data.projects);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data.projects);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load projects"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    getProjectUrls(selected.name)
      .then(setUrls)
      .catch((e) => setError(e.message));
  }, [selected]);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      const project = await createProject(newName.trim());
      setNewName("");
      setSelected(project);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
    }
  }

  async function handleRun(kind: JobKind) {
    if (!selected) return;
    await submitJob({ kind, project: selected.name });
  }

  async function submitJob(payload: { kind: JobKind; project?: string; s3_prefix?: string | null }) {
    try {
      await createJob(payload);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to start ${payload.kind}`);
    }
  }

  async function handleAddUrls() {
    if (!selected || !addText.trim()) return;
    const urlsToAdd = addText.split(/[\n,]+/).map((u) => u.trim()).filter(Boolean);
    try {
      await addProjectUrls(selected.name, urlsToAdd);
      setAddText("");
      await refreshUrls();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add URLs");
    }
  }

  async function handleUploadCsv(file: File) {
    if (!selected) return;
    try {
      await uploadProjectUrlsCsv(selected.name, file);
      await refreshUrls();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to upload CSV");
    }
  }

  async function handleRemoveSelected() {
    if (!selected || selectedUrls.length === 0) return;
    try {
      await removeProjectUrls(selected.name, selectedUrls);
      setSelectedUrls([]);
      await refreshUrls();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove URLs");
    }
  }

  async function handleRequeueSelected() {
    if (!selected || selectedUrls.length === 0) return;
    try {
      await requeueFailedUrls(selected.name, selectedUrls);
      setSelectedUrls([]);
      await refreshUrls();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to requeue URLs");
    }
  }

  async function refreshUrls() {
    if (!selected) return;
    const data = await getProjectUrls(selected.name);
    setUrls(data);
    await refresh();
  }

  function toggleUrl(url: string) {
    setSelectedUrls((prev) =>
      prev.includes(url) ? prev.filter((u) => u !== url) : [...prev, url],
    );
  }

  if (loading) return <Loader />;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Projects" subtitle="Output_<name> folders: URL lists, scraping runs, analysis and exports." />

      {error && <div className="mb-6"><Err message={error} /></div>}

      <div className="flex gap-3 mb-8">
        <Input
          value={newName}
          onChange={setNewName}
          placeholder="New project name"
          className="max-w-xs"
        />
        <Btn primary onClick={handleCreate}>Create project</Btn>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2 space-y-3">
          {projects.length === 0 && <Empty label="No projects yet." />}
          {projects.map((project) => (
            <button
              key={project.name}
              onClick={() => { setSelected(project); setSelectedUrls([]); }}
              className={`w-full rounded-xl border p-4 text-left transition ${
                selected?.name === project.name
                  ? "border-gray-500 bg-gray-900"
                  : "border-gray-800 bg-gray-900/50 hover:bg-gray-900"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-white">Output_{project.name}</span>
                <StatusBadge label={project.status} />
              </div>
              <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs text-gray-400">
                <div><p className="text-lg font-semibold text-white">{project.urls_pending}</p>pending</div>
                <div><p className="text-lg font-semibold text-white">{project.urls_done}</p>done</div>
                <div><p className="text-lg font-semibold text-white">{project.creators_saved}</p>saved</div>
                <div><p className="text-lg font-semibold text-white">{project.outputs.length}</p>outputs</div>
              </div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-3 space-y-6">
          {!selected ? (
            <Card><Empty label="Select a project on the left." /></Card>
          ) : (
            <>
              <Card title={`Output_${selected.name} — actions`}>
                <div className="flex flex-wrap gap-2">
                  <Btn primary onClick={() => handleRun("scrape")}>Scrape</Btn>
                  <Btn onClick={() => handleRun("analyze")}>Analyze</Btn>
                  <Btn onClick={() => handleRun("export")}>Export</Btn>
                  <Btn onClick={() => handleRun("full")}>Full pipeline</Btn>
                  <Btn
                    onClick={() => submitJob({
                      kind: "full",
                      project: selected.name,
                      s3_prefix: s3Prefix.trim() || null,
                    })}
                    disabled={!s3Prefix.trim()}
                  >
                    Full pipeline + S3
                  </Btn>
                  <Btn danger onClick={() => deleteProject(selected.name).then(() => { setSelected(null); refresh(); })}>
                    Delete
                  </Btn>
                </div>
                <div className="mt-4 max-w-xl">
                  <label className="block">
                    <span className="mb-1 block text-xs font-medium text-gray-400">S3 destination prefix</span>
                    <input
                      value={s3Prefix}
                      onChange={(e) => setS3Prefix(e.target.value)}
                      placeholder={`kreatos/${selected.name}`}
                      className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
                    />
                  </label>
                  <p className="mt-2 text-xs text-gray-500">
                    Runs scrape, analysis, exports, then uploads the project output folder to this S3 prefix.
                  </p>
                </div>
                <p className="mt-3 text-xs text-gray-500">
                  Runs are queued as background <Link href="/jobs" className="text-blue-400 hover:underline">jobs</Link>;
                  progress is visible on the Jobs page.
                </p>
              </Card>

              <Card title="URL list">
                <div className="space-y-3">
                  <textarea
                    value={addText}
                    onChange={(e) => setAddText(e.target.value)}
                    placeholder="Instagram usernames or profile URLs, one per line"
                    rows={3}
                    className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
                  />
                  <div className="flex flex-wrap gap-2">
                    <Btn onClick={handleAddUrls}>Add URLs</Btn>
                    <Btn onClick={() => fileRef.current?.click()}>Upload CSV</Btn>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".csv,text/csv"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleUploadCsv(f);
                        e.target.value = "";
                      }}
                    />
                    {urls && (urls.pending_count > 0 || urls.done_count > 0) && (
                      <>
                        <Btn danger onClick={handleRemoveSelected} disabled={selectedUrls.length === 0}>
                          Remove selected
                        </Btn>
                        <Btn onClick={handleRequeueSelected} disabled={selectedUrls.length === 0}>
                          Requeue failed
                        </Btn>
                      </>
                    )}
                  </div>
                </div>

                {urls && (urls.pending.length > 0 || urls.done.length > 0) ? (
                  <div className="mt-4 max-h-96 overflow-y-auto rounded-lg border border-gray-800">
                    <table className="w-full text-left text-sm">
                      <thead className="sticky top-0 bg-gray-900 text-xs text-gray-500">
                        <tr>
                          <th className="p-2 w-8" />
                          <th className="p-2">URL</th>
                          <th className="p-2 w-20">State</th>
                        </tr>
                      </thead>
                      <tbody>
                        {urls.pending.map((url) => (
                          <UrlRow key={url} url={url} state="pending" selected={selectedUrls.includes(url)} onToggle={toggleUrl} />
                        ))}
                        {urls.done.map((url) => (
                          <UrlRow key={url} url={url} state="done" selected={selectedUrls.includes(url)} onToggle={toggleUrl} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="mt-4"><Empty label="No URLs yet — add some above." /></div>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function UrlRow({
  url,
  state,
  selected,
  onToggle,
}: {
  url: string;
  state: "pending" | "done";
  selected: boolean;
  onToggle: (url: string) => void;
}) {
  const username = url.split("/").filter(Boolean).pop() ?? url;
  return (
    <tr className="border-t border-gray-800/60 hover:bg-gray-900/40">
      <td className="p-2 pl-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(url)}
          className="accent-white"
        />
      </td>
      <td className="p-2">
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
          @{username}
        </a>
      </td>
      <td className="p-2">
        <StatusBadge label={state} tone={state === "pending" ? "amber" : "green"} />
      </td>
    </tr>
  );
}