"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { adminMe, type MenuItem, type MenuTree } from "@/lib/api";

const GROUP_LABELS: Record<string, string> = {
  MAIN: "Main",
  INTELLIGENCE: "Intelligence",
  ENGAGEMENT: "Engagement",
  ACCOUNTS: "Accounts",
  MARKETPLACE: "Marketplace",
  CAMPAIGNS: "Campaigns",
  DATA: "Data",
  AUTOMATION: "Automation",
  SYSTEM: "System",
};

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function hrefForItem(item: MenuItem): string {
  return item.feature === item.key
    ? item.path
    : `${item.path}?workspace=${encodeURIComponent(item.key)}`;
}

export default function Nav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [menus, setMenus] = useState<MenuTree>({});
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    adminMe()
      .then((me) => {
        if (me.menus) setMenus(me.menus);
      })
      .catch(() => {});
  }, []);

  const groups = Object.entries(menus)
    .map(([group, items]) => [group, items as MenuItem[]] as const)
    .filter(([, items]) => items.length > 0);

  return (
    <aside className="sticky top-0 flex h-screen flex-col border-r border-slate-800 bg-[#07111f] w-60 shrink-0">
      <div className="px-6 py-6 border-b border-gray-800">
        <p className="text-lg font-bold tracking-tight">KreatOS</p>
        <p className="text-xs text-gray-500 mt-1">Instagram intelligence</p>
      </div>

      <nav className="flex flex-col gap-3 p-3 overflow-y-auto">
        {groups.map(([group, items]) => {
          const isCollapsed = collapsed[group];
          return (
            <div key={group}>
              <button
                type="button"
                onClick={() => setCollapsed((c) => ({ ...c, [group]: !c[group] }))}
                className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-300"
              >
                <span>{GROUP_LABELS[group] ?? group}</span>
                <span className={`transition-transform ${isCollapsed ? "" : "rotate-180"}`}>▾</span>
              </button>
              {!isCollapsed && (
                <div className="mt-1 flex flex-col gap-0.5">
                  {items.map((item) => {
                    const isSubmenu = item.feature !== item.key;
                    const active = isActive(pathname, item.path) &&
                      (!isSubmenu || searchParams.get("workspace") === item.key);
                    return (
                      <Link
                        key={item.key}
                        href={hrefForItem(item)}
                        className={
                          active && !isSubmenu
                            ? "flex items-center gap-2 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white"
                            : isSubmenu
                              ? "flex items-center gap-2 rounded-lg px-3 py-1.5 pl-8 text-xs text-gray-500 hover:bg-gray-900 hover:text-gray-200"
                              : "flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-900 hover:text-white"
                        }
                      >
                        <span className="text-sm leading-none">{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="mt-auto flex items-center justify-between border-t border-slate-800 px-4 py-4">
        <span className="flex items-center gap-2 text-[10px] font-medium text-emerald-400"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />System Online</span>
        <span className="text-[10px] text-slate-600">v2.5.0</span>
      </div>
    </aside>
  );
}