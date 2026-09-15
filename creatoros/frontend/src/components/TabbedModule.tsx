"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { adminMe, type MenuItem, type MenuTree } from "@/lib/api";

export default function TabbedModule({
  featureKey,
  title,
  subtitle,
  intro,
}: {
  featureKey: string;
  title: string;
  subtitle?: string;
  intro?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [menus, setMenus] = useState<MenuTree>({});
  const [tab, setTab] = useState("");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("25");
  const [message, setMessage] = useState("");

  useEffect(() => {
    adminMe()
      .then((me) => {
        if (me.menus) setMenus(me.menus);
      })
      .catch(() => {});
  }, []);

  const subs: MenuItem[] = Object.values(menus)
    .flat()
    .filter((item) => item.key.startsWith(`${featureKey}:`))
    .sort((a, b) => a.order - b.order);

  const requestedTab = searchParams.get("workspace") ?? "";
  const active = subs.find((s) => s.key === requestedTab) ?? subs.find((s) => s.key === tab) ?? subs[0];

  function selectTab(key: string) {
    setTab(key);
    router.replace(`${pathname}?workspace=${encodeURIComponent(key)}`, { scroll: false });
  }

  function runWorkspace() {
    if (!query.trim()) {
      setMessage("Enter a search value before running this workspace.");
      return;
    }
    setMessage(`${active?.label ?? title} request prepared for “${query.trim()}” with a limit of ${limit}. Connect the provider in Settings to run live collection.`);
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
      {subtitle ? <p className="mt-1 text-sm text-gray-400">{subtitle}</p> : null}

      {subs.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2 border-b border-gray-800 pb-px">
          {subs.map((sub) => (
            <button
              key={sub.key}
              onClick={() => selectTab(sub.key)}
              className={
                active?.key === sub.key
                  ? "rounded-t-lg border-b-2 border-white px-3 py-2 text-sm font-medium text-white"
                  : "rounded-t-lg border-b-2 border-transparent px-3 py-2 text-sm text-gray-500 hover:text-gray-300"
              }
            >
              {sub.label}
            </button>
          ))}
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-5">
        <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Live workspace</p>
              <h2 className="mt-1 text-lg font-semibold text-white">{active?.label ?? title}</h2>
              <p className="mt-1 text-sm text-gray-500">{intro ?? `Configure and run ${active?.label ?? title.toLowerCase()} from this workspace.`}</p>
            </div>
            <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[11px] text-blue-300">Configured</span>
          </div>
          <label className="mt-6 block">
            <span className="mb-1 block text-xs font-medium text-gray-400">Search or input</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") runWorkspace(); }} placeholder={`Enter ${active?.label?.toLowerCase() ?? "a value"}`} className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600" />
          </label>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="block"><span className="mb-1 block text-xs font-medium text-gray-400">Result limit</span><input type="number" min="1" max="500" value={limit} onChange={(event) => setLimit(event.target.value)} className="w-full rounded-lg border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-gray-600" /></label>
            <div className="flex items-end gap-2"><button type="button" onClick={runWorkspace} className="rounded-lg bg-white px-4 py-3 text-sm font-medium text-black hover:bg-gray-200">Run workspace</button><button type="button" onClick={() => { setQuery(""); setMessage(""); }} className="rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-gray-300 hover:bg-gray-700">Clear</button></div>
          </div>
          {message && <div className="mt-5 rounded-lg border border-blue-900 bg-blue-950/30 p-3 text-sm text-blue-300">{message}</div>}
        </section>
        <aside className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500">Workflow</p>
          <h2 className="mt-1 text-lg font-semibold text-white">{active?.label ?? title} options</h2>
          <div className="mt-5 space-y-3 text-sm text-gray-400"><p>Input is validated before a request is prepared.</p><p>Use Jobs for background work and Projects for saved profile data.</p><p>Provider credentials and session settings are managed centrally.</p></div>
          <div className="mt-6 flex flex-wrap gap-2"><Link href="/jobs" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">Open Jobs</Link><Link href="/settings" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800">Configure Settings</Link></div>
        </aside>
      </div>
    </div>
  );
}