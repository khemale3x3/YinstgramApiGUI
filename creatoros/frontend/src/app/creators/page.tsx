"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  databaseStatus,
  formatNumber,
  getCreator,
  getCreatorPosts,
  getSettings,
  listProjects,
  uploadProjectUrlsCsv,
  type CreatorPost,
  type CreatorProfile,
  type DatabaseStatus,
  type Project,
  type Settings,
} from "@/lib/api";

function toCsv(profile: CreatorProfile, posts: CreatorPost[]): string {
  const esc = (value: string) => `"${String(value).replace(/"/g, '""')}"`;
  const rows: string[] = [
    ["username", "full_name", "followers", "following", "posts", "is_private", "is_verified", "category", "biography"].map(esc).join(","),
    [profile.username, profile.full_name, profile.followers, profile.following, profile.media_count, profile.is_private, profile.is_verified, profile.category, profile.biography].map((value) => esc(String(value))).join(","),
    "",
    ["shortcode", "media_type", "taken_at", "likes", "comments", "plays", "views", "location", "caption"].map(esc).join(","),
    ...posts.map((post) => [post.shortcode, post.media_type, post.taken_at ?? "", post.likes, post.comments, post.plays, post.views, post.location ?? "", post.caption].map((value) => esc(String(value))).join(",")),
  ];
  return rows.join("\n");
}

export default function CreatorsPage() {
  const [username, setUsername] = useState("");
  const [profile, setProfile] = useState<CreatorProfile | null>(null);
  const [posts, setPosts] = useState<CreatorPost[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [database, setDatabase] = useState<DatabaseStatus | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(false);
  const [csvBusy, setCsvBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([listProjects(), databaseStatus(), getSettings()])
      .then(([projectResponse, db, appSettings]) => {
        setProjects(projectResponse.projects);
        setSelectedProject(projectResponse.projects[0]?.name ?? "");
        setDatabase(db);
        setSettings(appSettings);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load creator workspace"));
  }, []);

  async function analyze() {
    const query = username.trim().replace(/^@/, "");
    if (!query) return;
    setLoading(true);
    setError("");
    setMessage("");
    setProfile(null);
    setPosts([]);
    try {
      const [creator, recent] = await Promise.all([getCreator(query), getCreatorPosts(query, 25)]);
      setProfile(creator);
      setPosts(recent);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creator analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCsv(file: File) {
    if (!selectedProject) {
      setError("Create or select a project before importing creator URLs.");
      return;
    }
    setCsvBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await uploadProjectUrlsCsv(selectedProject, file);
      setMessage(`Imported ${result.added} creator URL(s) into ${selectedProject}. Start a scrape from Projects when ready.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV import failed");
    } finally {
      setCsvBusy(false);
    }
  }

  function exportCsv() {
    if (!profile) return;
    const url = URL.createObjectURL(new Blob([toCsv(profile, posts)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${profile.username}-creatoros.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const sqlServer = database?.remote;
  const postgres = settings?.postgres;
  const surface = "rounded-xl border border-slate-800/90 bg-[#0a1424]";
  const inputStyle = "w-full rounded-lg border border-slate-700 bg-[#07101d] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500/70 focus:ring-2 focus:ring-blue-500/20";

  return (
    <div className="min-h-full w-full bg-[#030a14] px-4 py-5 text-slate-200 sm:px-6 lg:px-7 xl:px-8">
      <div className="w-full min-w-0">
        <header className="flex flex-col gap-4 border-b border-slate-800/80 pb-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-blue-400/80"><span>Intelligence</span><span className="text-slate-600">/</span><span>Creators</span></div>
            <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">Creators</h1>
            <p className="mt-1 text-sm text-slate-400">Profile analysis and post collection with CSV export.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/projects" className="rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2.5 text-sm text-slate-300 transition hover:border-slate-600 hover:bg-slate-800">Open projects</Link>
            {profile && <button onClick={exportCsv} className="rounded-lg border border-slate-700 bg-slate-900/70 px-3.5 py-2.5 text-sm text-slate-300 transition hover:border-slate-600 hover:bg-slate-800">Export CSV</button>}
            <button onClick={() => inputRef.current?.focus()} className="rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/15 transition hover:bg-blue-400">+ Add Creator</button>
          </div>
        </header>

        {error && <div className="mt-5 rounded-lg border border-red-900/70 bg-red-950/40 p-4 text-sm text-red-300">{error}</div>}
        {message && <div className="mt-5 rounded-lg border border-emerald-900/70 bg-emerald-950/30 p-4 text-sm text-emerald-300">{message}</div>}

        <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className={`${surface} p-5 xl:col-span-8`}>
            <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Live lookup</p><h2 className="mt-1 text-lg font-semibold text-white">Analyze a creator</h2><p className="mt-1 text-xs text-slate-500">Fetch profile intelligence and the latest 25 posts from Instagram.</p></div><span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[11px] text-blue-300">API connected</span></div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row"><input ref={inputRef} value={username} onChange={(event) => setUsername(event.target.value)} onKeyDown={(event) => event.key === "Enter" && analyze()} placeholder="Username or Instagram profile URL" className={`${inputStyle} flex-1`} /><button onClick={analyze} disabled={loading || !username.trim()} className="rounded-lg bg-blue-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50">{loading ? "Analyzing..." : "Analyze"}</button></div>
          </div>

          <div className={`${surface} p-5 xl:col-span-4`}>
            <div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Bulk intake</p><h2 className="mt-1 text-lg font-semibold text-white">Upload creator CSV</h2></div><span className="text-xl text-blue-400">⇧</span></div>
            <p className="mt-1 text-xs text-slate-500">Import usernames or Instagram URLs into a project for scraping and analysis.</p>
            <div className="mt-4 flex gap-2"><select value={selectedProject} onChange={(event) => setSelectedProject(event.target.value)} className={`${inputStyle} min-w-0 flex-1 py-2.5`} aria-label="CSV destination project"><option value="">Select project</option>{projects.map((project) => <option key={project.name} value={project.name}>{project.name}</option>)}</select><button onClick={() => document.getElementById("creator-csv")?.click()} disabled={csvBusy || !selectedProject} className="shrink-0 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-slate-200 transition hover:border-blue-500/60 disabled:opacity-50">{csvBusy ? "Importing..." : "Choose CSV"}</button><input id="creator-csv" type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleCsv(file); event.target.value = ""; }} /></div>
            {!projects.length && <p className="mt-3 text-xs text-amber-300">No projects yet. Create one in Projects before importing.</p>}
          </div>
        </section>

        <section className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4"><Metric label="Profiles analyzed" value={profile ? "1" : "0"} detail="This session" accent="blue" /><Metric label="Followers" value={profile ? formatNumber(profile.followers) : "—"} detail={profile ? `@${profile.username}` : "Awaiting creator"} accent="violet" /><Metric label="Posts collected" value={profile ? formatNumber(posts.length) : "0"} detail="Latest profile fetch" accent="emerald" /><Metric label="Data systems" value="2" detail="SQL Server + PostgreSQL" accent="amber" /></section>

        <section className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"><DatabaseCard title="SQL Server ingest" detail={sqlServer?.server || "Not configured"} status={sqlServer?.available ? "Connected" : "Not reachable"} tone={sqlServer?.available ? "green" : "amber"} extra={sqlServer?.table ? `Table · ${sqlServer.table}` : "Remote creator data target"} /><DatabaseCard title="PostgreSQL app store" detail={postgres ? `${postgres.host}:${postgres.port}/${postgres.name}` : "Loading configuration"} status={postgres?.configured ? "Configured" : "Not configured"} tone={postgres?.configured ? "green" : "amber"} extra={postgres ? `Schema · ${postgres.schema}` : "Runtime job and project store"} /></section>

        {profile ? <ProfileWorkspace profile={profile} posts={posts} surface={surface} /> : <EmptyWorkspace surface={surface} />}
      </div>
    </div>
  );
}

function Metric({ label, value, detail, accent }: { label: string; value: string; detail: string; accent: "blue" | "violet" | "emerald" | "amber" }) {
  return <div className="rounded-xl border border-slate-800/90 bg-[#0a1424] p-4"><div className={`mb-3 h-1 w-10 rounded-full bg-${accent}-500`} /><p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold text-white">{value}</p><p className="mt-1 truncate text-xs text-slate-500">{detail}</p></div>;
}

function DatabaseCard({ title, detail, status, tone, extra }: { title: string; detail: string; status: string; tone: "green" | "amber"; extra: string }) {
  return <div className="rounded-xl border border-slate-800/90 bg-[#0a1424] p-4"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-3"><span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone === "green" ? "bg-emerald-500/10 text-emerald-300" : "bg-amber-500/10 text-amber-300"}`}>◈</span><div><h2 className="text-sm font-semibold text-white">{title}</h2><p className="mt-0.5 text-xs text-slate-500">{extra}</p></div></div><span className={`flex items-center gap-1.5 text-xs ${tone === "green" ? "text-emerald-300" : "text-amber-300"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{status}</span></div><p className="mt-4 truncate font-mono text-xs text-slate-400">{detail}</p></div>;
}

function EmptyWorkspace({ surface }: { surface: string }) {
  return <section className={`${surface} mt-4 flex min-h-[300px] items-center justify-center p-8`}><div className="max-w-md text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-xl text-blue-300">◎</div><h2 className="mt-4 text-lg font-semibold text-white">Ready for creator intelligence</h2><p className="mt-2 text-sm leading-6 text-slate-500">Search a username or profile URL above to load profile metrics and collected posts. Use CSV intake for a larger project batch.</p></div></section>;
}

function ProfileWorkspace({ profile, posts, surface }: { profile: CreatorProfile; posts: CreatorPost[]; surface: string }) {
  return <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-12"><div className={`${surface} p-5 xl:col-span-4`}><div className="flex items-start justify-between"><div><p className="text-xs uppercase tracking-[0.14em] text-blue-300">Creator profile</p><h2 className="mt-2 text-xl font-semibold text-white">{profile.full_name || `@${profile.username}`}</h2><p className="mt-1 text-sm text-slate-400">@{profile.username}{profile.category ? ` · ${profile.category}` : ""}</p></div>{profile.is_verified && <span className="rounded-full bg-blue-500/15 px-2 py-1 text-[10px] font-semibold text-blue-300">Verified</span>}</div><p className="mt-5 line-clamp-4 text-sm leading-6 text-slate-400">{profile.biography || "No biography available."}</p><div className="mt-6 grid grid-cols-2 gap-3">{[["Followers", formatNumber(profile.followers)], ["Following", formatNumber(profile.following)], ["Posts", formatNumber(profile.media_count)], ["Visibility", profile.is_private ? "Private" : "Public"]].map(([label, value]) => <div key={label} className="rounded-lg border border-slate-800 bg-[#07101d] p-3"><p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p><p className="mt-1 text-sm font-semibold text-white">{value}</p></div>)}</div></div><div className={`${surface} min-w-0 overflow-hidden xl:col-span-8`}><div className="flex items-center justify-between border-b border-slate-800 px-5 py-4"><div><h2 className="text-sm font-semibold text-white">Collected posts</h2><p className="mt-1 text-xs text-slate-500">{posts.length} items returned from the latest profile fetch</p></div><span className="rounded-md border border-slate-700 px-2 py-1 text-[10px] uppercase tracking-wider text-slate-500">Live data</span></div>{posts.length ? <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-[#07101d] text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-5 py-3">Media</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Likes</th><th className="px-4 py-3">Comments</th><th className="px-4 py-3">Plays</th><th className="px-4 py-3">Caption</th></tr></thead><tbody className="divide-y divide-slate-800/80">{posts.map((post) => <tr key={post.pk} className="bg-[#0a1424] transition hover:bg-slate-800/30"><td className="px-5 py-2">{post.thumbnail_url ? <img src={post.thumbnail_url} alt="" className="h-10 w-10 rounded-md border border-slate-700 object-cover" /> : <span className="text-xs text-slate-600">—</span>}</td><td className="px-4 py-2 capitalize text-slate-300">{post.media_type}</td><td className="px-4 py-2 text-white">{formatNumber(post.likes)}</td><td className="px-4 py-2 text-white">{formatNumber(post.comments)}</td><td className="px-4 py-2 text-white">{post.plays ? formatNumber(post.plays) : "—"}</td><td className="max-w-[340px] truncate px-4 py-2 text-slate-400">{post.caption || "—"}</td></tr>)}</tbody></table></div> : <p className="p-8 text-center text-sm text-slate-500">No posts collected for this creator.</p>}</div></section>;
}