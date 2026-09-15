"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  formatNumber,
  marketplaceCategories,
  marketplaceDiscover,
  MARKETPLACE_SUBCATEGORIES,
  recentProfiles,
  searchProfiles,
  type ProfileRecord,
} from "@/lib/api";
import { Pagination } from "@/components/ui";

type Filter = "username" | "category" | "audience";

export default function DiscoveryPage() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(() => searchParams.get("query") ?? "");
  const [filter, setFilter] = useState<Filter>("username");
  const [rows, setRows] = useState<ProfileRecord[] | null>(null);
  const [recent, setRecent] = useState<ProfileRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [discoverable, setDiscoverable] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 24;

  useEffect(() => {
    let alive = true;
    marketplaceCategories()
      .then((d) => {
        // Check if Instagram is connected by looking at category counts
        // If no categories have data beyond generic, Instagram may not be configured
        setDiscoverable(true);
      })
      .catch(() => {
        setDiscoverable(false);
      });
    recentProfiles(12)
      .then((d) => alive && setRecent(d.results))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const initialQuery = searchParams.get("query")?.trim();
    if (initialQuery) {
      setQuery(initialQuery);
      void run(initialQuery);
    }
  }, [searchParams]);

  async function run(input = query) {
    const q = input.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setSearched(true);
    setPage(1);
    try {
      const d = await searchProfiles(q, 100);
      setRows(d.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setRows(null);
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setQuery("");
    setRows(null);
    setSearched(false);
    setPage(1);
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Discovery</h1>
          <p className="mt-1 text-sm text-gray-400">
            One search across every saved creator — by username, category or audience keyword.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/marketplace" className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900">
            Marketplace
          </Link>
          <Link href="/campaigns" className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900">
            Campaigns
          </Link>
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        <div className="flex rounded-lg border border-gray-700 bg-gray-950 p-1">
          {(
            [
              ["username", "Username"],
              ["category", "Category"],
              ["audience", "Audience"],
            ] as Array<[Filter, string]>
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                filter === key ? "bg-white font-medium text-black" : "text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={
            filter === "username"
              ? "e.g. fitness, natgeo…"
              : filter === "category"
                ? "e.g. fashion, travel…"
                : "e.g. gym, foodie, sustainability…"
          }
          className="flex-1 rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
        />
        <button
          onClick={() => void run()}
          disabled={loading || !query.trim() || !discoverable}
          className="rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
        {searched && (
          <button onClick={clear} className="rounded-lg border border-gray-700 px-4 py-2.5 text-sm text-gray-400 hover:text-white">
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{error}</div>
      )}
      
      {discoverable === false && (
        <div className="mt-8 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
          <p className="font-medium text-red-300">Instagram discovery is not configured</p>
          <p className="mt-2 text-sm text-gray-400">
            Connect an Instagram session in Settings → Instagram Accounts to enable creator discovery and search.
          </p>
        </div>
      )}

      {searched && !loading && !error && rows !== null && (
        <div className="mt-6">
          {rows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
              <p className="text-sm text-gray-400">
                No creators match in the saved store. Broaden your {filter} query or collect more profiles.
              </p>
            </div>
          ) : (
            <>
              <CreatorGrid rows={rows.slice((page - 1) * pageSize, page * pageSize)} caption={`${rows.length} matches in the saved store`} />
              <Pagination page={page} pageSize={pageSize} total={rows.length} onPage={setPage} />
            </>
          )}
        </div>
      )}

      {!searched && (
        <div className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-200">Recently collected</h2>
            <Link href="/marketplace" className="text-xs text-blue-400 hover:underline">
              Browse all →
            </Link>
          </div>
          {recent.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
              <p className="text-sm text-gray-400">
                No creators collected yet.{" "}
                <Link href="/creators" className="text-blue-400 hover:underline">
                  Analyze your first profile
                </Link>{" "}
                or run an ingest job to start building your store.
              </p>
            </div>
          ) : (
            <>
              <CreatorGrid rows={recent.slice((page - 1) * pageSize, page * pageSize)} />
              <Pagination page={page} pageSize={pageSize} total={recent.length} onPage={setPage} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function CreatorGrid({ rows, caption }: { rows: ProfileRecord[]; caption?: string }) {
  return (
    <>
      {caption ? <p className="mb-4 text-xs text-gray-600">{caption}</p> : null}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {rows.map((p) => (
          <Link
            key={p.username}
            href={`/creators/${p.username}`}
            className="flex items-center gap-3 rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 hover:border-gray-700"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">
                {p.full_name || `@${p.username}`}
              </p>
              <p className="truncate text-xs text-gray-500">
                @{p.username}
                {p.category ? ` · ${p.category}` : ""}
              </p>
            </div>
            <span className="shrink-0 text-sm text-gray-300">{formatNumber(p.followers)}</span>
          </Link>
        ))}
      </div>
    </>
  );
}