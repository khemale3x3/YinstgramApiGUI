"use client";

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

      <div className="mt-8 min-h-[360px] rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-8">
        <p className="text-sm font-medium text-gray-300">
          {active?.label ?? title}
        </p>
        <p className="mt-2 text-sm text-gray-500">
          {intro ??
            `This ${active?.label ?? "view"} is part of the KreatOS module map. Its API
            surface is wired and ready — the workflow panel ships in the next build pass.`}
        </p>
      </div>
    </div>
  );
}