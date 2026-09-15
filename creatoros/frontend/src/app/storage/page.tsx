"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Btn, Card, Empty, Err, Input, Loader, PageHeader, StatusBadge } from "@/components/ui";
import {
  downloadS3Key,
  listS3Keys,
  storageStatus,
  uploadS3File,
  type StorageStatus,
} from "@/lib/api";

export default function StoragePage() {
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [keys, setKeys] = useState<string[]>([]);
  const [prefix, setPrefix] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [uploadKey, setUploadKey] = useState("");
  const [downloadKey, setDownloadKey] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [st, keysData] = await Promise.all([storageStatus(), listS3Keys(prefix)]);
      setStatus(st);
      setKeys(keysData.keys);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load storage");
    } finally {
      setLoading(false);
    }
  }, [prefix]);

  useEffect(() => {
    Promise.all([storageStatus(), listS3Keys(prefix)])
      .then(([st, keysData]) => {
        setStatus(st);
        setKeys(keysData.keys);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load storage"))
      .finally(() => setLoading(false));
  }, [prefix]);

  async function handleUpload(file: File) {
    if (!uploadKey) return;
    setBusy("upload");
    setError("");
    setNotice("");
    try {
      await uploadS3File(uploadKey, file);
      setNotice(`Uploaded ${file.name} → s3://…/${uploadKey}`);
      setUploadKey("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleDownload(key: string) {
    setBusy(`dl:${key}`);
    setError("");
    try {
      const url = await downloadS3Key(key);
      const a = document.createElement("a");
      a.href = url;
      a.download = key.split("/").pop() ?? "file";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Loader />;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Storage" subtitle="S3 object storage for project exports and artifacts." />

      {error && <div className="mb-6"><Err message={error} /></div>}
      {notice && (
        <div className="mb-6 rounded-lg border border-emerald-800 bg-emerald-950/50 p-3 text-sm text-emerald-300">
          {notice}
        </div>
      )}

      <div className="mb-8">
        <Card title="Connection">
          <div className="flex items-center gap-3">
            {status?.available ? (
              <StatusBadge label="connected" tone="green" />
            ) : (
              <StatusBadge label="not configured" tone="amber" />
            )}
            <span className="text-sm text-gray-400">{status?.type ?? "S3"}</span>
            {!status?.available && (
              <span className="text-xs text-gray-500">
                Set S3_ACCESS_KEY / S3_SECRET_KEY in backend/.env.
              </span>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3 mb-8">
        <Card title="Upload a file">
          <div className="space-y-3">
            <Input value={uploadKey} onChange={setUploadKey} placeholder="Key, e.g. exports/myfile.csv" />
            <Btn onClick={() => fileRef.current?.click()} disabled={busy !== null || !uploadKey}>
              {busy === "upload" ? "Uploading…" : "Choose file"}
            </Btn>
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  handleUpload(f);
                  e.target.value = "";
                }
              }}
            />
          </div>
        </Card>

        <Card title="Download a key" className="lg:col-span-2">
          <div className="flex gap-3">
            <Input value={downloadKey} onChange={setDownloadKey} placeholder="Key, e.g. exports/myfile.csv" className="flex-1" />
            <Btn onClick={() => handleDownload(downloadKey)} disabled={busy !== null || !downloadKey}>
              {busy?.startsWith("dl:") ? "Downloading…" : "Download"}
            </Btn>
          </div>
        </Card>
      </div>

      <Card
        title={`Objects (${keys.length})`}
        className={keys.length ? "mb-16" : ""}
      >
        <div className="mb-4 flex gap-3">
          <Input value={prefix} onChange={setPrefix} placeholder="Prefix filter (optional)" className="flex-1" />
          <Btn onClick={refresh}>Refresh</Btn>
        </div>
        {keys.length === 0 ? (
          <Empty label="No objects found." />
        ) : (
          <div className="max-h-[28rem] overflow-y-auto rounded-lg border border-gray-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-gray-900 text-xs text-gray-500">
                <tr>
                  <th className="p-2">Key</th>
                  <th className="p-2 w-24">Action</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key} className="border-t border-gray-800/60 hover:bg-gray-900/40">
                    <td className="p-2 font-mono text-xs text-gray-300 break-all">{key}</td>
                    <td className="p-2">
                      <Btn size="sm" onClick={() => handleDownload(key)} disabled={busy !== null}>
                        Download
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}