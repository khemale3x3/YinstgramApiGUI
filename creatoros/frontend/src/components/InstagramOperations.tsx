"use client";

import { useState } from "react";
import { instagramAction } from "@/lib/api";

export default function InstagramOperations({ mode }: { mode: "publishing" | "direct" | "hashtags" }) {
  const [action, setAction] = useState(mode === "publishing" ? "publish_photo" : mode === "direct" ? "direct_send" : "hashtag_info");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key: string, value: string) => setFields((current) => ({ ...current, [key]: value }));
  const field = (key: string, placeholder: string, type = "text") => <input type={type} value={fields[key] ?? ""} onChange={(event) => set(key, event.target.value)} placeholder={placeholder} className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600" />;
  async function run() {
    setBusy(true); setError(""); setResult("");
    try {
      const payload = { ...fields, limit: Number(fields.limit || 25), paths: fields.paths?.split(",").map((value) => value.trim()).filter(Boolean) };
      const response = await instagramAction(action, payload);
      setResult(JSON.stringify(response, null, 2));
    } catch (e) { setError(e instanceof Error ? e.message : "Instagram operation failed"); }
    finally { setBusy(false); }
  }
  const options = mode === "publishing" ? [["publish_photo", "Publish photo"], ["publish_video", "Publish video"], ["publish_album", "Publish carousel"]] : mode === "direct" ? [["direct_send", "Send direct message"], ["comments", "Read comments"], ["comment", "Reply to comment"]] : [["hashtag_info", "Hashtag information"], ["hashtag_recent", "Recent hashtag posts"], ["hashtag_top", "Top hashtag posts"]];
  return <div className="mt-8 grid gap-6 lg:grid-cols-5"><section className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-3"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Authenticated Instagram API</p><h2 className="mt-1 text-lg font-semibold text-white">{mode === "publishing" ? "Publish content" : mode === "direct" ? "Manage community" : "Search hashtags"}</h2><p className="mt-1 text-sm text-gray-500">Requires an authenticated Instagram account session. Operations are persisted to the scraper database.</p><select value={action} onChange={(event) => { setAction(event.target.value); setFields({}); }} className="mt-5 w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white">{options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><div className="mt-4 space-y-3">{action.startsWith("publish_") && <>{field("path", "Absolute local media path")}{field("caption", "Caption")}{action === "publish_album" && field("paths", "Comma-separated media paths")}</>}{action === "direct_send" && <>{field("user_id", "Instagram user ID", "number")}{field("text", "Message")}</>}{action === "comment" && <>{field("media_id", "Media ID")}{field("text", "Reply text")}</>}{action === "comments" && <>{field("media_id", "Media ID")}{field("limit", "Comment limit", "number")}</>}{action.startsWith("hashtag_") && <>{field("hashtag", "Hashtag without #")}{action !== "hashtag_info" && field("limit", "Media limit", "number")}</>}</div><button type="button" onClick={() => void run()} disabled={busy} className="mt-5 rounded-lg bg-white px-4 py-3 text-sm font-medium text-black hover:bg-gray-200 disabled:opacity-50">{busy ? "Running..." : "Run operation"}</button>{error && <p className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-3 text-sm text-red-300">{error}</p>}</section><aside className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-2"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Result</p>{result ? <pre className="mt-4 max-h-[28rem] overflow-auto whitespace-pre-wrap text-xs text-emerald-300">{result}</pre> : <p className="mt-4 text-sm text-gray-500">Results and operation errors appear here after the authenticated API responds.</p>}</aside></div>;
}