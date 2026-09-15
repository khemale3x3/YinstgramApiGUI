"use client";

import { useEffect, useState } from "react";
import { Card, Err, Field, Loader } from "@/components/ui";
import {
  createJob,
  listProjects,
  uploadProjectUrlsCsv,
  type Project,
} from "@/lib/api";

export default function DataPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [exportProject, setExportProject] = useState("");
  const [exportBusy, setExportBusy] = useState(false);
  const [exportMsg, setExportMsg] = useState("");

  const [importProject, setImportProject] = useState("");
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState("");

  useEffect(() => {
    listProjects()
      .then((res) => {
        setProjects(res.projects);
        if (res.projects[0]) {
          setExportProject(res.projects[0].name);
          setImportProject(res.projects[0].name);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load projects"))
      .finally(() => setLoading(false));
  }, []);

  async function runExport() {
    if (!exportProject) return;
    setExportBusy(true);
    setExportMsg("");
    try {
      await createJob({ kind: "export", project: exportProject, with_csv: true });
      setExportMsg(`Export job started for ${exportProject}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExportBusy(false);
    }
  }

  async function onImportCsv(file: File) {
    if (!importProject) return;
    setImportBusy(true);
    setImportMsg("");
    try {
      const res = await uploadProjectUrlsCsv(importProject, file);
      setImportMsg(`Imported ${res.added} URLs into ${importProject}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImportBusy(false);
    }
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">Import / Export</h1>
      <p className="mt-1 text-sm text-gray-400">
        Move creator URLs in and out of projects — wired to the jobs backend.
      </p>

      {error && <div className="mt-6"><Err message={error} /></div>}

      {loading ? (
        <Loader />
      ) : (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Export project → CSV">
            <div className="flex flex-col gap-4">
              <Field label="Project">
                <select
                  value={exportProject}
                  onChange={(e) => setExportProject(e.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600"
                >
                  {projects.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name} ({p.creators_saved} creators)
                    </option>
                  ))}
                </select>
              </Field>
              <button
                onClick={runExport}
                disabled={exportBusy || !exportProject}
                className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
              >
                {exportBusy ? "Starting…" : "Run export job"}
              </button>
              {exportMsg && <p className="text-sm text-emerald-400">{exportMsg}</p>}
            </div>
          </Card>

          <Card title="Import URLs (CSV) into project">
            <div className="flex flex-col gap-4">
              <Field label="Project">
                <select
                  value={importProject}
                  onChange={(e) => setImportProject(e.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600"
                >
                  {projects.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="CSV file (one Instagram URL per line)">
                <p className="text-xs text-gray-500">
                  CSV with one Instagram URL per line, no header required.
                </p>
              </Field>
              <FileUpload
                disabled={importBusy || !importProject}
                onFile={onImportCsv}
                busy={importBusy}
              />
              {importMsg && <p className="text-sm text-emerald-400">{importMsg}</p>}
            </div>
          </Card>
        </div>
      )}

      <p className="mt-8 text-xs text-gray-600">
        Bulk operations, deduplication, data quality and refresh land with the import/export workflow pass.
      </p>
    </div>
  );
}

function FileUpload({ disabled, onFile, busy }: { disabled: boolean; onFile: (f: File) => void; busy: boolean }) {
  return (
    <label
      className={
        disabled
          ? "flex w-full cursor-not-allowed items-center justify-center rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm font-medium text-gray-500"
          : "flex w-full cursor-pointer items-center justify-center rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-700"
      }
    >
      {busy ? "Importing…" : "Choose CSV and import"}
      <input
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.currentTarget.value = "";
        }}
      />
    </label>
  );
}