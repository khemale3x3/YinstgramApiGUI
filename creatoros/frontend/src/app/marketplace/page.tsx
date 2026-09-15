"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  MARKETPLACE_SUBCATEGORIES,
  marketplaceCategories,
  marketplaceCreatorsFiltered,
  marketplaceDiscover,
  marketplaceFavorite,
  marketplaceUnfavorite,
  type MarketplaceCategory,
  type ProfileRecord,
} from "@/lib/api";

type ViewMode = "grid" | "list" | "mirror" | "table" | "atlas";
type SortMode = "followers" | "media" | "recent";
const VIEW_MODES: Array<{ key: ViewMode; label: string }> = [
  { key: "grid", label: "Grid" }, { key: "list", label: "List" },
  { key: "mirror", label: "Mirror" }, { key: "table", label: "Table" },
  { key: "atlas", label: "Atlas" },
];
const WORKSPACES = ["marketplace:find", "marketplace:hashtags", "marketplace:locations", "marketplace:all", "marketplace:saved", "marketplace:lists", "marketplace:analysis"];

function titleFor(key: string) {
  return ({
    "marketplace:find": "Find Creators", "marketplace:hashtags": "Hashtag Creators",
    "marketplace:locations": "Location Creators", "marketplace:all": "All Creators",
    "marketplace:saved": "Saved Creators", "marketplace:lists": "Creator Lists",
    "marketplace:analysis": "Creator Analysis",
  } as Record<string, string>)[key] ?? "Marketplace";
}

export default function MarketplacePage() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const workspace = params.get("workspace") ?? "marketplace:all";
  const [categories, setCategories] = useState<MarketplaceCategory[]>([]);
  const [creators, setCreators] = useState<ProfileRecord[]>([]);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [category, setCategory] = useState("generic");
  const [query, setQuery] = useState("");
  const [minFollowers, setMinFollowers] = useState(0);
  const [verified, setVerified] = useState(false);
  const [sort, setSort] = useState<SortMode>("followers");
  const viewParam = params.get("view");
  const view: ViewMode = viewParam === "list" || viewParam === "mirror" || viewParam === "table" || viewParam === "atlas" ? viewParam : "grid";
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { marketplaceCategories().then((result) => setCategories(result.categories)).catch(() => setCategories([])); }, []);
  useEffect(() => {
    let alive = true;
    marketplaceCreatorsFiltered({ category, query, minFollowers, verified, sort, limit: 200 })
      .then((result) => alive && setCreators(result.creators))
      .catch((err) => alive && setError(err instanceof Error ? err.message : "Failed to load creators"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [category, query, minFollowers, verified, sort]);

  function selectWorkspace(key: string) { router.replace(`${pathname}?workspace=${encodeURIComponent(key)}&view=${view}`, { scroll: false }); }
  function selectView(nextView: ViewMode) { router.replace(`${pathname}?workspace=${encodeURIComponent(workspace)}&view=${nextView}`, { scroll: false }); }
  async function discover() {
    if (category === "generic") return;
    setBusy(true); setError("");
    try { const result = await marketplaceDiscover(category, 40); setCreators(result.creators); setCategories(result.category_counts); }
    catch (err) { setError(err instanceof Error ? err.message : "Creator discovery failed"); }
    finally { setBusy(false); }
  }
  async function toggleFavorite(username: string) {
    const saved = favorites.has(username);
    setFavorites((current) => { const next = new Set(current); if (saved) next.delete(username); else next.add(username); return next; });
    try { await (saved ? marketplaceUnfavorite(username) : marketplaceFavorite(username)); }
    catch (err) {
      setFavorites((current) => { const next = new Set(current); if (saved) next.add(username); else next.delete(username); return next; });
      setError(err instanceof Error ? err.message : "Could not update saved creator");
    }
  }
  const visibleCreators = workspace === "marketplace:saved" ? creators.filter((creator) => favorites.has(creator.username)) : creators;

  return <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold tracking-tight text-white">{titleFor(workspace)}</h1><p className="mt-1 text-sm text-gray-400">Live creator profiles from the Marketplace API.</p></div><button onClick={discover} disabled={busy || category === "generic"} className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-40">{busy ? "Finding..." : "Find Creators"}</button></div>
    <div className="mt-6 flex flex-wrap gap-2 border-b border-gray-800 pb-3">{WORKSPACES.map((key) => <button key={key} onClick={() => selectWorkspace(key)} className={workspace === key ? "rounded-lg bg-white px-3 py-2 text-xs font-medium text-black" : "rounded-lg border border-gray-800 px-3 py-2 text-xs text-gray-400 hover:text-white"}>{titleFor(key)}</button>)}</div>
    <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-4"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search username, name, bio" className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-white" /><select value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-white">{MARKETPLACE_SUBCATEGORIES.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select><select value={sort} onChange={(event) => setSort(event.target.value as SortMode)} className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-white"><option value="followers">Most followers</option><option value="media">Most media</option><option value="recent">Recently collected</option></select><input type="number" min="0" value={minFollowers || ""} onChange={(event) => setMinFollowers(Number(event.target.value) || 0)} placeholder="Minimum followers" className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-white" /></div>
    <label className="mt-3 inline-flex items-center gap-2 text-sm text-gray-400"><input type="checkbox" checked={verified} onChange={(event) => setVerified(event.target.checked)} /> Verified only</label>
    <div className="mt-5 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-gray-500">{visibleCreators.length} profiles</p><div className="flex gap-1 rounded-lg border border-gray-800 p-1">{VIEW_MODES.map((mode) => <button key={mode.key} onClick={() => selectView(mode.key)} className={view === mode.key ? "rounded bg-gray-700 px-3 py-1.5 text-xs text-white" : "px-3 py-1.5 text-xs text-gray-500 hover:text-white"}>{mode.label}</button>)}</div></div>
    {error && <p className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
    {loading ? <p className="mt-8 text-sm text-gray-500">Loading profiles...</p> : <ProfileResults creators={visibleCreators} view={view} favorites={favorites} onFavorite={toggleFavorite} />}
    <div className="mt-6 flex flex-wrap gap-2 text-xs text-gray-500">{categories.map((item) => <span key={item.key} className="rounded-full border border-gray-800 px-3 py-1">{item.label}: {item.count}</span>)}</div>
  </div>;
}

function ProfileResults({ creators, view, favorites, onFavorite }: { creators: ProfileRecord[]; view: ViewMode; favorites: Set<string>; onFavorite: (username: string) => void }) {
  if (creators.length === 0) return <div className="mt-8 rounded-xl border border-dashed border-gray-800 p-10 text-center text-sm text-gray-500">No profiles match these filters.</div>;
  if (view === "table") return <div className="mt-6 overflow-x-auto rounded-xl border border-gray-800"><table className="w-full text-left text-sm"><thead className="bg-gray-900 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Profile</th><th className="px-4 py-3">Followers</th><th className="px-4 py-3">Media</th><th className="px-4 py-3">Category</th></tr></thead><tbody>{creators.map((creator) => <tr key={creator.username} className="border-t border-gray-800 hover:bg-gray-900"><td className="px-4 py-3"><ProfileLink creator={creator} /></td><td className="px-4 py-3">{creator.followers.toLocaleString()}</td><td className="px-4 py-3">{creator.media_count.toLocaleString()}</td><td className="px-4 py-3 text-gray-400">{creator.category || "-"}</td></tr>)}</tbody></table></div>;
  return <div className={view === "grid" || view === "atlas" ? "mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" : "mt-6 flex flex-col gap-3"}>{creators.map((creator) => <article key={creator.username} className={view === "mirror" ? "rounded-xl border border-gray-800 bg-gradient-to-r from-gray-900 to-gray-950 p-5 text-center" : "rounded-xl border border-gray-800 bg-gray-900/50 p-4"}><ProfileLink creator={creator} /><div className="mt-3 flex items-center justify-between text-xs text-gray-400"><span>{creator.followers.toLocaleString()} followers</span><span>{creator.media_count.toLocaleString()} media</span></div><button onClick={() => onFavorite(creator.username)} className="mt-3 w-full rounded border border-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-800">{favorites.has(creator.username) ? "Saved" : "Save profile"}</button></article>)}</div>;
}

function ProfileLink({ creator }: { creator: ProfileRecord }) { return <Link href={`/creators/${encodeURIComponent(creator.username)}`} className="block min-w-0 hover:text-blue-300"><p className="truncate font-medium text-white">{creator.full_name || `@${creator.username}`}</p><p className="truncate text-xs text-gray-500">@{creator.username}{creator.is_verified ? " · Verified" : ""}</p><p className="mt-2 line-clamp-2 text-xs text-gray-400">{creator.biography || "No biography available."}</p></Link>; }
