"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ProfileDropdown from "@/components/ProfileDropdown";

export default function TopHeader() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  function submitSearch() {
    const value = query.trim();
    if (value) router.push(`/discovery?query=${encodeURIComponent(value)}`);
  }

  return (
    <header className="sticky top-0 z-20 flex min-h-[58px] items-center justify-between gap-4 border-b border-slate-800/80 bg-[#07111f]/95 px-4 backdrop-blur sm:px-6">
      <div className="min-w-0 flex-1">
        <label className="relative block max-w-[520px]">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">⌕</span>
          <input
            ref={searchRef}
            aria-label="Global search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && submitSearch()}
            placeholder="Search creators, accounts, hashtags, or anything..."
            className="w-full rounded-lg border border-slate-700/80 bg-[#0a1728] py-2 pl-9 pr-12 text-xs text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-blue-500/60 focus:ring-2 focus:ring-blue-500/15"
          />
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-500">⌘K</span>
        </label>
      </div>
      <div className="flex items-center gap-3">
        <Link href="/monitoring" aria-label="Notifications and system activity" title="Notifications and system activity" className="relative rounded-lg p-2 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white">♧<span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-blue-400" /></Link>
        <div className="hidden h-6 w-px bg-slate-800 sm:block" />
        <ProfileDropdown menuPlacement="top-full right-0 mt-3 left-auto bottom-auto" />
      </div>
    </header>
  );
}
