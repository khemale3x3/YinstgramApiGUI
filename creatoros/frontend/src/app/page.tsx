"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import PostThumb from "@/components/PostThumb";
import StatCard from "@/components/StatCard";
import {
  adminMe,
  createJob,
  databaseStatus,
  formatNumber,
  formatWhen,
  getCreator,
  getCreatorPosts,
  getDashboard,
  isAdmin,
  listJobs,
  listProjects,
  type CreatorPost,
  type CreatorProfile,
  type DashboardSnapshot,
  type DatabaseStatus,
  type FeatureFlag,
  type Job,
  type MenuItem,
  type MenuTree,
  type Project,
} from "@/lib/api";

const EMPTY: DashboardSnapshot = {
  stats: {
    creators: 0,
    posts_analyzed: 0,
    campaigns: { total: 0, matches: 0, by_status: {} },
    accounts: { cookie_total: 0, cookie_active: 0, cookie_backup: 0, instagrapi: 0, total: 0 },
    storage_available: false,
    jobs: { running: 0, failed: 0, completed: 0, cancelled: 0, queued: 0 },
  },
  top_creators: [],
  discovery: { total: 0, recent: 0, categories: [], top_candidates: [] },
  recent_activity: [],
  growth: [],
};

export default function Home() {
  return isAdmin() ? <AdminHome /> : <UserHome />;
}

// ------------------------------------------------------------------ admin
function AdminHome() {
  const searchParams = useSearchParams();
  const workspace = searchParams.get("workspace") ?? "dashboard:overview";
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(EMPTY);
  const [db, setDb] = useState<DatabaseStatus | null>(null);
  const [error, setError] = useState("");

  const [username, setUsername] = useState("");
  const [creator, setCreator] = useState<CreatorProfile | null>(null);
  const [posts, setPosts] = useState<CreatorPost[]>([]);
  const [searching, setSearching] = useState(false);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [triggerProject, setTriggerProject] = useState("");
  const [triggerKind, setTriggerKind] = useState<"scrape" | "analyze" | "full">("scrape");
  const [triggerStatus, setTriggerStatus] = useState("");

  useEffect(() => {
    let alive = true;
    const poll = () => {
      getDashboard()
        .then((d) => alive && setSnapshot(d))
        .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load dashboard"));
    };
    poll();
    const timer = setInterval(poll, 5000);
    databaseStatus()
      .then((st) => alive && setDb(st))
      .catch(() => {});
    listJobs(8)
      .then((d) => alive && setRecentJobs(d.jobs))
      .catch(() => {});
    listProjects()
      .then((d) => {
        if (!alive) return;
        setProjects(d.projects);
        setTriggerProject(d.projects[0]?.name ?? "");
      })
      .catch(() => {});
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  async function searchCreator() {
    const query = username.trim().replace(/^@/, "");
    if (!query) return;
    setSearching(true);
    setCreator(null);
    setPosts([]);
    try {
      const [profile, recent] = await Promise.all([
        getCreator(query),
        getCreatorPosts(query, 6),
      ]);
      setCreator(profile);
      setPosts(recent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setSearching(false);
    }
  }

  async function triggerPipeline() {
    if (!triggerProject) {
      setTriggerStatus("Create or select a project before triggering a job.");
      return;
    }
    setTriggerStatus("");
    try {
      await createJob({ kind: triggerKind, project: triggerProject });
      setTriggerStatus(`${triggerKind} job queued for ${triggerProject}.`);
    } catch (e) {
      setTriggerStatus(e instanceof Error ? e.message : "Unable to queue job");
    }
  }

  const { stats, top_creators, recent_activity, growth } = snapshot;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-400">KreatOS control center · {workspaceLabel(workspace)}</p>
        </div>
        <Link
          href="/creators"
          className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-gray-200"
        >
          + Add Creator
        </Link>
      </div>

      {error && <div className="mt-6"><ErrText message={error} /></div>}

      <DashboardWorkspace
        workspace={workspace}
        projects={projects}
        project={triggerProject}
        setProject={setTriggerProject}
        kind={triggerKind}
        setKind={setTriggerKind}
        onTrigger={() => void triggerPipeline()}
        message={triggerStatus}
      />

      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Creators" value={formatNumber(stats.creators)} />
        <StatCard title="Accounts" value={formatNumber(stats.accounts.total)} />
        <StatCard title="Posts Analyzed" value={formatNumber(stats.posts_analyzed)} />
        <StatCard
          title="Jobs"
          value={`${formatNumber(stats.jobs.running)} running`}
          hint={`${formatNumber(stats.jobs.queued)} queued`}
        />
      </div>

      <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Creator Growth</h2>
          <Link href="/database" className="text-xs text-blue-400 hover:underline">
            Database →
          </Link>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Creators first collected per day, from the profile store.
        </p>
        <GrowthChart data={growth} />
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="mb-2 text-sm font-semibold text-gray-200">Top Creators</h2>
            <Link href="/creators" className="text-xs text-blue-400 hover:underline">
              View all →
            </Link>
          </div>
          {top_creators.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">
              No scraped creators yet —{" "}
              <Link href="/creators" className="text-blue-400 hover:underline">analyze one</Link>.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {top_creators.map((c) => (
                <Link
                  key={c.username}
                  href={`/creators/${c.username}`}
                  className="flex items-center gap-3 rounded-lg px-2 py-1 hover:bg-gray-800/40"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-xs font-bold text-white">
                    {Math.round(c.score)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white">
                      {c.full_name || `@${c.username}`}
                    </p>
                    <p className="text-xs text-gray-500">
                      @{c.username}
                      {c.category ? ` · ${c.category}` : ""}
                    </p>
                  </span>
                  <span className="shrink-0 text-sm text-gray-300">
                    {formatNumber(c.followers)} <span className="text-xs text-gray-500">followers</span>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h2 className="mb-4 text-sm font-semibold text-gray-200">Recent Activity</h2>
          {recent_activity.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">No activity recorded yet.</p>
          ) : (
            <div className="flex flex-col gap-2.5">
              {recent_activity.map((a, i) => (
                <div key={i} className="flex items-start justify-between gap-4 text-sm">
                  <div className="min-w-0">
                    <p className="truncate text-gray-200">{a.action}</p>
                    <p className="truncate text-xs text-gray-500">
                      {a.target ? `${a.target} · ` : ""}{a.detail}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-gray-600">
                    {formatWhen(a.time)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Background Jobs</h2>
          <Link href="/jobs" className="text-xs text-blue-400 hover:underline">
            Manage jobs →
          </Link>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Live status from the job store, polled every few seconds.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <JobLegend color="bg-amber-400" label="Running" value={stats.jobs.running} />
          <JobLegend color="bg-gray-400" label="Queued" value={stats.jobs.queued} />
          <JobLegend color="bg-emerald-500" label="Completed" value={stats.jobs.completed} />
          <JobLegend color="bg-red-500" label="Failed" value={stats.jobs.failed} />
          <JobLegend color="bg-blue-400" label="Cancelled" value={stats.jobs.cancelled} />
        </div>
        {recentJobs.length > 0 ? (
          <div className="mt-4 flex flex-col gap-2">
            {recentJobs.map((j) => (
              <Link
                key={j.id}
                href="/jobs"
                className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm hover:border-gray-700"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: dotFor(j.status) }} />
                  <span className="truncate text-gray-200">{j.kind}</span>
                  {j.project ? <span className="truncate text-xs text-gray-600">· {j.project}</span> : null}
                </span>
                <span className="shrink-0 text-xs text-gray-500">
                  {formatNumber(j.progress)}% · {formatWhen(j.created_at)}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-500">
            No jobs yet — start one from the{" "}
            <Link href="/jobs" className="text-blue-400 hover:underline">Jobs</Link>{" "}
            page to see live progress here.
          </p>
        )}
      </div>

      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <h2 className="mb-4 text-sm font-semibold text-gray-200">System Health</h2>
        <div className="flex flex-wrap gap-3 text-sm">
          <HealthPill label="API" ok />
          <HealthPill
            label="Database"
            ok={Boolean(db?.local?.available)}
            sub={db?.local?.type}
          />
          <HealthPill
            label="SQL Server"
            ok={Boolean(db?.remote?.available)}
            sub={db?.remote?.available ? "connected" : "not configured"}
          />
          <HealthPill label="Storage (S3)" ok={stats.storage_available} sub={stats.storage_available ? "connected" : "not configured"} />
          <HealthPill label="Sessions" ok={stats.accounts.total > 0} sub={`${stats.accounts.total} available`} />
        </div>
      </div>

      <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <h2 className="mb-2 text-sm font-semibold text-gray-200">Creator Discovery</h2>
        <p className="mb-4 text-xs text-gray-500">
          Profile and content lookup for any Instagram username.
        </p>
        <div className="flex gap-3">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchCreator()}
            placeholder="Instagram username (e.g. natgeo)"
            className="flex-1 rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
          />
          <button
            onClick={searchCreator}
            disabled={searching}
            className="rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black disabled:opacity-50"
          >
            {searching ? "Analyzing…" : "Analyze"}
          </button>
        </div>

        {creator && (
          <div className="mt-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-white">
                  {creator.full_name || `@${creator.username}`}
                </h3>
                <p className="text-sm text-gray-400">
                  @{creator.username}
                  {creator.category ? ` · ${creator.category}` : ""}
                  {creator.is_verified ? " · verified" : ""}
                </p>
              </div>
              <a
                href={`https://www.instagram.com/${creator.username}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:underline"
              >
                Open on Instagram →
              </a>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <StatCard title="Followers" value={formatNumber(creator.followers)} />
              <StatCard title="Following" value={formatNumber(creator.following)} />
              <StatCard title="Posts" value={formatNumber(creator.media_count)} />
            </div>
            {posts.length > 0 && (
              <div className="mt-6 grid grid-cols-3 gap-3">
                {posts.map((post) => (
                  <PostThumb key={post.pk} post={post} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------- user
function UserHome() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(EMPTY);
  const [features, setFeatures] = useState<FeatureFlag[]>([]);
  const [menus, setMenus] = useState<MenuTree>({});
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    adminMe()
      .then((me) => {
        if (!alive) return;
        setEmail(me.email);
        setName(me.name ?? "");
        if (me.features) setFeatures(me.features.filter((f) => f.enabled));
        if (me.menus) setMenus(me.menus);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load workspace"));
    getDashboard()
      .then((d) => alive && setSnapshot(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const rootPaths = new Map<string, string>();
  for (const items of Object.values(menus)) {
    for (const item of items as MenuItem[]) {
      if (item.feature === item.key) rootPaths.set(item.feature, item.path);
    }
  }

  const { stats } = snapshot;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          {name ? `${name.split(" ")[0]}'s Workspace` : "My Workspace"}
        </h1>
        <p className="mt-1 text-sm text-gray-400">
          {email} · creator account
        </p>
      </div>

      {error && <div className="mt-6"><ErrText message={error} /></div>}

      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Creators" value={formatNumber(stats.creators)} />
        <StatCard title="Accounts" value={formatNumber(stats.accounts.total)} />
        <StatCard title="Posts Analyzed" value={formatNumber(stats.posts_analyzed)} />
        <StatCard title="Jobs Running" value={formatNumber(stats.jobs.running)} />
      </div>

      <div className="mt-10">
        <h2 className="text-sm font-semibold text-gray-200">Your modules</h2>
        <p className="mt-1 text-xs text-gray-500">
          The features enabled for your account — full administration and system tools
          are reserved for the admin console.
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.length === 0 && (
          <p className="py-6 text-sm text-gray-500">No modules enabled yet.</p>
        )}
        {features.map((feature) => {
          const path = rootPaths.get(feature.key) ?? "/";
          return (
            <Link
              key={feature.key}
              href={path}
              className="group rounded-xl border border-gray-800 bg-gray-900/50 p-5 hover:border-gray-700 hover:bg-gray-900"
            >
              <p className="text-sm font-semibold text-white group-hover:text-gray-100">
                {feature.label}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {feature.group} module
              </p>
              <p className="mt-3 text-xs text-blue-400 opacity-80 group-hover:opacity-100">
                Open module →
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function JobLegend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      <span className="text-gray-400">{label}</span>
      <span className="font-semibold text-white">{formatNumber(value)}</span>
    </div>
  );
}

function dotFor(status: string) {
  switch (status) {
    case "running":
      return "#fbbf24";
    case "pending":
      return "#9ca3af";
    case "succeeded":
      return "#10b981";
    case "failed":
      return "#ef4444";
    case "cancelled":
      return "#60a5fa";
    default:
      return "#6b7280";
  }
}

function workspaceLabel(workspace: string) {
  return {
    "dashboard:overview": "Overview",
    "dashboard:activity": "Activity",
    "dashboard:health": "System Health",
    "dashboard:jobs": "Jobs",
    "dashboard:alerts": "Alerts",
  }[workspace] ?? "Overview";
}

function DashboardWorkspace({
  workspace,
  projects,
  project,
  setProject,
  kind,
  setKind,
  onTrigger,
  message,
}: {
  workspace: string;
  projects: Project[];
  project: string;
  setProject: (value: string) => void;
  kind: "scrape" | "analyze" | "full";
  setKind: (value: "scrape" | "analyze" | "full") => void;
  onTrigger: () => void;
  message: string;
}) {
  const label = workspaceLabel(workspace);
  const isJobs = workspace === "dashboard:jobs";
  const isAlerts = workspace === "dashboard:alerts";
  return (
    <section className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Dashboard workspace</p>
          <h2 className="mt-1 text-lg font-semibold text-white">{label}</h2>
          <p className="mt-1 text-sm text-gray-500">
            {isJobs ? "Trigger and monitor scrape, analysis, and full pipeline jobs." : isAlerts ? "Review failed jobs and operational warnings from the live job store." : `Review ${label.toLowerCase()} data from the connected application services.`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2"><Link href="/jobs" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">Open Jobs</Link><Link href="/monitoring?workspace=automation%3Ascheduled" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">Schedule</Link><Link href="/settings" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">Configure</Link></div>
      </div>
      {(isJobs || workspace === "dashboard:overview") && <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"><select value={project} onChange={(event) => setProject(event.target.value)} className="rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white"><option value="">Select project</option>{projects.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select><select value={kind} onChange={(event) => setKind(event.target.value as "scrape" | "analyze" | "full")} className="rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white"><option value="scrape">Scrape</option><option value="analyze">Analyze</option><option value="full">Full pipeline</option></select><button type="button" onClick={onTrigger} disabled={!project} className="rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-black hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50">Trigger job</button></div>}
      {message && <p className="mt-3 rounded-lg border border-blue-900 bg-blue-950/30 p-3 text-sm text-blue-300">{message}</p>}
      {isAlerts && <div className="mt-5 rounded-lg border border-amber-900/60 bg-amber-950/20 p-4 text-sm text-amber-200">Failed and cancelled jobs are listed in Jobs, where they can be retried or cancelled.</div>}
    </section>
  );
}

function GrowthChart({ data }: { data: Array<{ date: string; count: number }> }) {
  if (!data || data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No collection history yet — daily creator counts will plot here as profiles are stored.
      </p>
    );
  }
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="mt-4">
      <div className="flex items-end gap-1" style={{ height: 140 }}>
        {data.map((d) => (
          <div
            key={d.date}
            className="group relative flex-1 rounded-t bg-gray-700/60 hover:bg-blue-500/70"
            style={{ height: `${Math.max(6, Math.round((d.count / max) * 100))}%` }}
          >
            <div className="pointer-events-none absolute bottom-full left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white group-hover:block">
              {d.date} · {formatNumber(d.count)}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1 text-[10px] text-gray-600">
        {data.length <= 14 ? (
          data.map((d) => (
            <span key={d.date} className="flex-1 truncate text-center">
              {d.date.slice(5)}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-600">
            {data[0].date} → {data[data.length - 1].date}
          </span>
        )}
      </div>
    </div>
  );
}

function HealthPill({ label, ok, sub }: { label: string; ok: boolean; sub?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-gray-800 bg-gray-950 px-3 py-2">
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`} />
      <span className="text-gray-300">{label}</span>
      {sub ? <span className="text-xs text-gray-600">· {sub}</span> : null}
    </div>
  );
}

function ErrText({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
      {message}
    </div>
  );
}