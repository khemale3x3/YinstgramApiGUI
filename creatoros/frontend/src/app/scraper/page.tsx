"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  addProjectUrls,
  createJob,
  databaseStatus,
  getSettings,
  listJobs,
  listProjects,
  type DatabaseStatus,
  type Job,
  type Project,
  type Settings,
} from "@/lib/api";

type Mode = "instagram" | "network";
type Status = { kind: "error" | "success"; text: string } | null;

const surface = "rounded-xl border border-slate-800/90 bg-[#0a1424]";
const inputStyle = "w-full rounded-lg border border-slate-700 bg-[#07101d] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500/70 focus:ring-2 focus:ring-blue-500/20";

export default function ScraperPage() {
  const searchParams = useSearchParams();
  const mode: Mode = searchParams.get("workspace") === "scraper:network" ? "network" : "instagram";
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState("");
  const [profile, setProfile] = useState("");
  const [bulk, setBulk] = useState("");
  const [direction, setDirection] = useState<"followers" | "following">("followers");
  const [limit, setLimit] = useState("100");
  const [database, setDatabase] = useState<DatabaseStatus | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const networkFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([listProjects(), databaseStatus(), getSettings()])
      .then(([projectResponse, db, appSettings]) => {
        setProjects(projectResponse.projects);
        setProject(projectResponse.projects[0]?.name ?? "");
        setDatabase(db);
        setSettings(appSettings);
      })
      .catch((error) => setStatus({ kind: "error", text: error instanceof Error ? error.message : "Failed to load scraper workspace" }));
  }, []);

  useEffect(() => {
    let active = true;
    const refresh = () => listJobs(200).then((response) => { if (active) setJobs(response.jobs); }).catch(() => {});
    void refresh();
    const timer = window.setInterval(refresh, 2500);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  async function startInstagram(urls: string[], message: string) {
    if (!project || !urls.length) return;
    setBusy(true);
    setStatus(null);
    try {
      await createJob({ kind: "scrape", project, urls, test_limit: urls.length === 1 ? 1 : null });
      setStatus({ kind: "success", text: message });
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "Could not start Instagram scrape" });
    } finally { setBusy(false); }
  }

  async function scrapeSingle() {
    const value = profile.trim();
    if (value) await startInstagram([value], `Instagram scrape started for ${value}. Track progress in Jobs.`);
  }

  async function scrapeBulk() {
    const urls = bulk.split(/[\n,]+/).map((value) => value.trim()).filter(Boolean);
    if (!project || !urls.length) return;
    setBusy(true);
    setStatus(null);
    try {
      const result = await addProjectUrls(project, urls);
      await createJob({ kind: "scrape", project });
      setBulk("");
      setStatus({ kind: "success", text: `Added ${result.added} profile(s) and started the bulk Instagram scrape.` });
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "Could not start bulk scrape" });
    } finally { setBusy(false); }
  }

  async function uploadInstagramCsv(file: File) {
    if (!project) return;
    const { valid, invalid, duplicates } = parseCsv(await file.text());
    if (!valid.length) {
      setStatus({ kind: "error", text: `CSV has no valid profiles. Invalid rows: ${invalid}; duplicates: ${duplicates}.` });
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      const result = await addProjectUrls(project, valid);
      await createJob({ kind: "scrape", project });
      setStatus({ kind: "success", text: `Validated ${valid.length} profile(s), imported ${result.added}, and started the bulk scrape. Invalid rows: ${invalid}; duplicates: ${duplicates}.` });
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "Could not import CSV" });
    } finally { setBusy(false); }
  }

  async function startNetwork(usernames: string[]) {
    if (!project || !usernames.length) return false;
    setBusy(true);
    setStatus(null);
    try {
      await createJob({ kind: "network_scrape", project, usernames, direction, test_limit: Number(limit) || 100 });
      setStatus({ kind: "success", text: `Started ${direction} collection for ${usernames.length} source profile(s). Results will be added to the project queue.` });
      return true;
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "Could not start network scrape" });
    } finally { setBusy(false); }
  }

  async function collectNetwork() {
    await startNetwork(profile.split(/[\n,]+/).map(normalizeUsername).filter(Boolean));
  }

  async function uploadNetworkCsv(file: File) {
    const { valid, invalid, duplicates } = parseCsv(await file.text());
    if (!valid.length) {
      setStatus({ kind: "error", text: `CSV has no valid profiles. Invalid rows: ${invalid}; duplicates: ${duplicates}.` });
      return;
    }
    const started = await startNetwork(valid.map(normalizeUsername));
    if (started) setStatus({ kind: "success", text: `Validated ${valid.length} source profile(s). Invalid rows: ${invalid}; duplicates: ${duplicates}.` });
  }

  const title = mode === "instagram" ? "Instagram Scraper" : "Followers / Followings Scraper";
  const subtitle = mode === "instagram" ? "Profile collection and post scraping with bulk CSV intake." : "Collect follower and following accounts into a project for profile scraping.";

  return (
    <div className="min-h-full w-full bg-[#030a14] px-4 py-5 text-slate-200 sm:px-6 lg:px-7 xl:px-8">
      <div className="w-full min-w-0">
        <header className="flex flex-col gap-4 border-b border-slate-800/80 pb-5 xl:flex-row xl:items-center xl:justify-between">
          <div><div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-blue-400/80"><span>Intelligence</span><span className="text-slate-600">/</span><span>Scraper</span><span className="text-slate-600">/</span><span>{mode === "instagram" ? "Instagram" : "Network"}</span></div><h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h1><p className="mt-1 text-sm text-slate-400">{subtitle}</p></div>
          <div className="flex flex-wrap items-center gap-2"><Link href="/projects" className="rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2.5 text-sm text-slate-300 transition hover:border-slate-600 hover:bg-slate-800">Open projects</Link><Link href="/jobs" className="rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2.5 text-sm text-slate-300 transition hover:border-slate-600 hover:bg-slate-800">Jobs</Link><Link href="/settings?workspace=settings%3Astorage" className="rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2.5 text-sm text-slate-300 transition hover:border-slate-600 hover:bg-slate-800">Save destination</Link></div>
        </header>
        {status && <div className={`mt-5 rounded-lg border p-4 text-sm ${status.kind === "error" ? "border-red-900/70 bg-red-950/40 text-red-300" : "border-emerald-900/70 bg-emerald-950/30 text-emerald-300"}`}>{status.text}</div>}
        {!projects.length ? <EmptyScraper /> : <>
          <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-12"><div className={`${surface} p-5 xl:col-span-8`}><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Live scrape</p><h2 className="mt-1 text-lg font-semibold text-white">{mode === "instagram" ? "Scrape an Instagram profile" : "Scrape followers or followings"}</h2><p className="mt-1 text-xs text-slate-500">{mode === "instagram" ? "Collect profile information and recent posts from Instagram." : "Collect follower and following accounts from an Instagram profile into a project."}</p></div><span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[11px] text-blue-300">API connected</span></div><label className="mt-5 block"><span className="mb-1 block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Project</span><select value={project} onChange={(event) => setProject(event.target.value)} className={inputStyle} aria-label="Scrape project">{projects.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label><div className="mt-3 flex flex-col gap-3 sm:flex-row"><input value={profile} onChange={(event) => setProfile(event.target.value)} placeholder={mode === "instagram" ? "Username or Instagram profile URL" : "Username or Instagram profile URL"} className={`${inputStyle} flex-1`} />{mode === "instagram" ? <button onClick={() => void scrapeSingle()} disabled={busy || !profile.trim() || !project} className="rounded-lg bg-blue-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Scraping..." : "Scrape"}</button> : <button onClick={() => void collectNetwork()} disabled={busy || !profile.trim() || !project} className="rounded-lg bg-blue-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Scraping..." : "Scrape"}</button>}</div>{mode === "network" && <div className="mt-3 flex items-center gap-3"><span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Network</span><select value={direction} onChange={(event) => setDirection(event.target.value as "followers" | "following")} className={`${inputStyle} max-w-xs`}><option value="followers">Followers</option><option value="following">Following</option></select><input type="number" min="1" max="5000" value={limit} onChange={(event) => setLimit(event.target.value)} className={`${inputStyle} max-w-xs`} aria-label="Maximum accounts" placeholder="Maximum accounts" /></div>}</div>
            <BulkCard mode={mode} project={project} setProject={setProject} projects={projects} bulk={bulk} setBulk={setBulk} busy={busy} onScrapeBulk={() => void scrapeBulk()} onInstagramCsv={(file) => void uploadInstagramCsv(file)} onNetworkCsv={(file) => void uploadNetworkCsv(file)} fileRef={fileRef} networkFileRef={networkFileRef} direction={direction} setDirection={setDirection} limit={limit} setLimit={setLimit} /></section>
          <section className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4"><Metric label="Profiles queued" value={String(jobs.filter((job) => job.project === project && ["queued", "running", "pending"].includes(job.status) && (mode === "network" ? job.kind === "network_scrape" : job.kind === "scrape")).reduce((total, job) => total + (Array.isArray(job.payload.urls) ? job.payload.urls.length : Array.isArray(job.payload.usernames) ? job.payload.usernames.length : 1), 0))} detail="Current scraping session" accent="blue" /><Metric label={mode === "instagram" ? "Profiles scraped" : "Profiles processed"} value={String(projects.find((item) => item.name === project)?.creators_saved ?? 0)} detail="Latest scraping run" accent="violet" /><Metric label={mode === "instagram" ? "Posts collected" : "Accounts collected"} value={String(jobs.filter((job) => job.project === project && job.status === "succeeded" && (mode === "network" ? job.kind === "network_scrape" : job.kind === "scrape")).reduce((total, job) => total + Number(job.result?.stats && typeof job.result.stats === "object" && "saved" in job.result.stats ? (job.result.stats as { saved?: number }).saved ?? 0 : job.result?.collected ?? 0), 0))} detail="Latest scraping run" accent="emerald" /><Metric label="Scrape jobs" value={String(jobs.filter((job) => job.project === project && ["queued", "running", "pending"].includes(job.status)).length)} detail="Queued + running" accent="amber" /></section>
          <section className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"><SystemCard title="SQL Server ingest" detail={database?.remote?.server || "Not configured"} status={database?.remote?.available ? "Connected" : "Not reachable"} /><SystemCard title="Scraped data destination" detail={settings?.storage.local_dir || settings?.storage.bucket || "Loading configuration"} status={settings?.storage.configured || settings?.storage.provider === "local" ? "Configured" : "Not configured"} /></section>
          <section className={`${surface} mt-4 flex min-h-[260px] items-center justify-center p-8`}><div className="max-w-md text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-xl text-blue-300">◎</div><h2 className="mt-4 text-lg font-semibold text-white">Ready for {mode === "instagram" ? "Instagram scraping" : "network collection"}</h2><p className="mt-2 text-sm leading-6 text-slate-500">Choose a project above, submit a source, and monitor the background job from Jobs.</p></div></section>
        </>}
      </div>
    </div>
  );
}

function normalizeUsername(value: string) { const clean = value.trim().replace(/^"|"$/g, "").replace(/^@/, ""); if (!clean.includes("instagram.com")) return clean; return clean.replace(/\?.*$/, "").replace(/\/$/, "").split("/").pop() ?? ""; }

function parseCsv(text: string) {
  const values = text.split(/[\r\n,]+/).map(normalizeUsername).filter((value) => value && value.toLowerCase() !== "username");
  const seen = new Set<string>();
  let duplicates = 0;
  const valid = values.filter((value) => {
    if (!/^[A-Za-z0-9_.]{1,30}$/.test(value)) return false;
    if (seen.has(value.toLowerCase())) { duplicates += 1; return false; }
    seen.add(value.toLowerCase());
    return true;
  });
  return { valid, invalid: values.length - valid.length - duplicates, duplicates };
}

function BulkCard({ mode, project, setProject, projects, bulk, setBulk, busy, onScrapeBulk, onInstagramCsv, onNetworkCsv, fileRef, networkFileRef, direction, setDirection, limit, setLimit }: { mode: Mode; project: string; setProject: (value: string) => void; projects: Project[]; bulk: string; setBulk: (value: string) => void; busy: boolean; onScrapeBulk: () => void; onInstagramCsv: (file: File) => void; onNetworkCsv: (file: File) => void; fileRef: React.RefObject<HTMLInputElement | null>; networkFileRef: React.RefObject<HTMLInputElement | null>; direction: "followers" | "following"; setDirection: (value: "followers" | "following") => void; limit: string; setLimit: (value: string) => void }) {
  return <div className={`${surface} p-5 xl:col-span-4`}><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Bulk intake</p><h2 className="mt-1 text-lg font-semibold text-white">{mode === "instagram" ? "Upload profile CSV" : "Upload source CSV"}</h2></div><span className="text-xl text-blue-400">⇧</span></div><p className="mt-1 text-xs text-slate-500">Destination project</p><select value={project} onChange={(event) => setProject(event.target.value)} className={`${inputStyle} mt-3`} aria-label="Scraper destination project">{projects.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select>{mode === "instagram" ? <><textarea value={bulk} onChange={(event) => setBulk(event.target.value)} placeholder="creator_one\ncreator_two" className={`${inputStyle} mt-3 min-h-24 resize-y`} /><div className="mt-3 flex gap-2"><button onClick={onScrapeBulk} disabled={busy || !bulk.trim()} className="rounded-lg bg-blue-500 px-3.5 py-2 text-sm font-semibold text-white disabled:opacity-50">Start bulk</button><button onClick={() => fileRef.current?.click()} disabled={busy} className="rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-slate-200 disabled:opacity-50">Choose CSV</button><input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) onInstagramCsv(file); event.target.value = ""; }} /></div></> : <><div className="mt-3 flex gap-2"><button onClick={() => setDirection("followers")} className={`flex-1 rounded-lg border px-3 py-2 text-xs ${direction === "followers" ? "border-blue-500 bg-blue-500/10 text-blue-300" : "border-slate-700 text-slate-400"}`}>Followers</button><button onClick={() => setDirection("following")} className={`flex-1 rounded-lg border px-3 py-2 text-xs ${direction === "following" ? "border-blue-500 bg-blue-500/10 text-blue-300" : "border-slate-700 text-slate-400"}`}>Followings</button></div><input type="number" min="1" max="5000" value={limit} onChange={(event) => setLimit(event.target.value)} className={`${inputStyle} mt-3`} placeholder="Limit per source" /><div className="mt-3"><button onClick={() => networkFileRef.current?.click()} disabled={busy} className="rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-slate-200 disabled:opacity-50">Choose source CSV</button><input ref={networkFileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) onNetworkCsv(file); event.target.value = ""; }} /></div></>}</div>;
}

function Metric({ label, value, detail, accent }: { label: string; value: string; detail: string; accent: "blue" | "violet" | "emerald" | "amber" }) { return <div className={`${surface} p-4`}><div className={`mb-3 h-1 w-10 rounded-full bg-${accent}-500`} /><p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p><p className="mt-1 truncate text-2xl font-semibold text-white">{value}</p><p className="mt-1 truncate text-xs text-slate-500">{detail}</p></div>; }
function SystemCard({ title, detail, status }: { title: string; detail: string; status: string }) { const good = status === "Connected" || status === "Configured"; return <div className={`${surface} p-4`}><div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-white">{title}</h2><p className="mt-1 text-xs text-slate-500">{detail}</p></div><span className={`text-xs ${good ? "text-emerald-300" : "text-amber-300"}`}>{status}</span></div></div>; }
function EmptyScraper() { return <section className={`${surface} mt-5 flex min-h-[330px] items-center justify-center p-8`}><div className="max-w-md text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-xl text-blue-300">◎</div><h2 className="mt-4 text-lg font-semibold text-white">Create a project before starting a scrape</h2><p className="mt-2 text-sm leading-6 text-slate-500">Create a project to store profile URLs, scraper results, posts, and network collections.</p><Link href="/projects" className="mt-5 inline-block rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-400">Open projects</Link></div></section>; }
