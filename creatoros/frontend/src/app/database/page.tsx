"use client";

import { useEffect, useState } from "react";
import { Btn, Card, Empty, Err, Input, Loader, PageHeader, Pagination, StatusBadge } from "@/components/ui";
import {
  databaseStatus,
  databaseTables,
  databaseViews,
  formatNumber,
  recentProfiles,
  searchProfiles,
  type DatabaseStatus,
  type DatabaseTable,
  type DatabaseView,
  type ProfileRecord,
} from "@/lib/api";

export default function DatabasePage() {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ProfileRecord[]>([]);
  const [recent, setRecent] = useState<ProfileRecord[]>([]);
  const [tables, setTables] = useState<DatabaseTable[]>([]);
  const [views, setViews] = useState<DatabaseView[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [resultsPage, setResultsPage] = useState(1);
  const [recentPage, setRecentPage] = useState(1);
  const pageSize = 12;

  useEffect(() => {
    Promise.all([databaseStatus(), recentProfiles(15), databaseViews(), databaseTables()])
      .then(([st, rec, vw, tb]) => {
        setStatus(st);
        setRecent(rec.results);
        setViews(vw.views);
        setTables(tb.tables);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load database"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const data = await searchProfiles(query.trim(), 50);
      setResults(data.results);
      setResultsPage(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  if (loading) return <Loader />;

  const local = status?.local;
  const remote = status?.remote;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Database" subtitle="Scraped-profile metadata (local SQLite) and SQL Server ingest target." />

      {error && <div className="mb-6"><Err message={error} /></div>}

      <div className="grid gap-4 sm:grid-cols-2 mb-8">
        <Card title="Local metadata store">
          <p className="text-2xl font-bold text-white">{local?.profiles ?? 0}</p>
          <p className="mt-1 text-xs text-gray-500">
            Type: <span className="text-gray-300">{local?.type ?? "—"}</span>
          </p>
          <div className="mt-2">
            <StatusBadge label={local?.available ? "available" : "unavailable"} tone={local?.available ? "green" : "red"} />
          </div>
        </Card>
        <Card title="SQL Server ingest target">
          <p className="text-sm text-gray-300">{remote?.server || "not configured"}</p>
          <p className="mt-1 text-xs text-gray-500">
            {remote?.type ?? "—"} · table {status?.remote?.table ?? "—"}
          </p>
          <div className="mt-2">
            <StatusBadge label={remote?.available ? "reachable" : "not reachable"} tone={remote?.available ? "green" : "amber"} />
          </div>
        </Card>
      </div>

      <Card title="Search profiles" className="mb-8">
        <div className="flex gap-3">
          <Input
            value={query}
            onChange={setQuery}
            placeholder="Username, name, bio or category…"
            className="flex-1"
          />
          <Btn primary onClick={handleSearch} disabled={searching || !query.trim()}>
            {searching ? "Searching…" : "Search"}
          </Btn>
        </div>
        {results.length > 0 && (
          <div className="mt-4">
            <>
            <ProfileTable profiles={results.slice((resultsPage - 1) * pageSize, resultsPage * pageSize)} />
            <Pagination page={resultsPage} pageSize={pageSize} total={results.length} onPage={setResultsPage} />
            </>
          </div>
        )}
      </Card>

      <Card title="Recently scraped">
        {recent.length === 0 ? (
          <Empty label="No profiles scraped yet — run a scrape job first." />
        ) : (
          <>
            <ProfileTable profiles={recent.slice((recentPage - 1) * pageSize, recentPage * pageSize)} />
            <Pagination page={recentPage} pageSize={pageSize} total={recent.length} onPage={setRecentPage} />
          </>
        )}
      </Card>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        <Card title="Tables">
          {tables.length === 0 ? (
            <Empty label="No tables returned." />
          ) : (
            <div className="space-y-4">
              {tables.map((t) => (
                <div key={t.name}>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-mono text-sm text-emerald-400">{t.name}</span>
                    <span className="text-xs text-gray-500">{t.rows} rows</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {t.columns.map((c) => (
                      <span
                        key={c.name}
                        className="rounded bg-gray-900 px-1.5 py-0.5 font-mono text-[10px] text-gray-400"
                        title={`${c.type}${c.pk ? " · PK" : ""}`}
                      >
                        {c.name}
                        {c.pk ? " 🔑" : ""}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Views / connections">
          {views.length === 0 ? (
            <Empty label="No views available in this store." />
          ) : (
            <div className="space-y-4">
              {views.map((v) => (
                <div key={v.name} className="rounded-lg border border-gray-800 bg-gray-950/40 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-sky-400">{v.name}</span>
                    <span className="text-xs text-gray-500">{v.rows} rows</span>
                  </div>
                  <p className="mt-1 text-[10px] font-mono text-gray-600">
                    {v.columns.join(", ")}
                  </p>
                  {v.error ? (
                    <p className="mt-1 text-xs text-red-400">{v.error}</p>
                  ) : (
                    <div className="mt-2 overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <tbody>
                          {v.sample.slice(0, 3).map((row, i) => (
                            <tr key={i} className="border-t border-gray-800/60">
                              <td className="py-1 pr-3 text-gray-300">
                                {String(row.username ?? row.status ?? row.category ?? row.action ?? "")}
                              </td>
                              <td className="py-1 pr-3 text-gray-500">
                                {String(row.created_at ?? row.followers ?? row.cnt ?? "").slice(0, 24)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function ProfileTable({ profiles }: { profiles: ProfileRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-gray-900 text-xs text-gray-500">
          <tr>
            <th className="p-2">Username</th>
            <th className="p-2">Name</th>
            <th className="p-2">Followers</th>
            <th className="p-2">Category</th>
            <th className="p-2">Scraped</th>
          </tr>
        </thead>
        <tbody>
          {profiles.map((profile) => (
            <tr key={profile.username} className="border-t border-gray-800/60 hover:bg-gray-900/40">
              <td className="p-2">
                <a
                  href={profile.url || `https://www.instagram.com/${profile.username}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  @{profile.username}
                </a>
              </td>
              <td className="p-2 text-gray-300">{profile.full_name || "—"}</td>
              <td className="p-2 text-gray-300">{formatNumber(profile.followers)}</td>
              <td className="p-2 text-gray-400">{profile.category || "—"}</td>
              <td className="p-2 text-xs text-gray-500">{profile.scraped_at?.slice(0, 16) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}