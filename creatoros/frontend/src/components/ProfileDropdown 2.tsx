"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearAuth, adminMe } from "@/lib/api";

interface DropdownItem {
  label: string;
  hint?: string;
  onSelect: () => void;
}

function useDropdownState() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (e.target instanceof Node && !(e.target as Element).closest("[data-profile-menu]")) {
        setOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return { open, setOpen };
}

function ProfileDropdown({ menuPlacement = "bottom-full left-0 mb-3" }: { menuPlacement?: string }) {
  const router = useRouter();
  const { open, setOpen } = useDropdownState();
  const [user, setUser] = useState<{ email: string; name: string; role: string; username?: string } | null>(null);

  useEffect(() => {
    adminMe()
      .then((me) => {
        setUser({
          email: me.email,
          name: me.name ?? "",
          role: me.role,
          username: me.username ?? "",
        });
      })
      .catch(() => {
        setUser(null);
      });
  }, []);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  const items: DropdownItem[] = [
    { label: "Profile", hint: "Your account overview", onSelect: () => go("/profile") },
    { label: "Account Settings", hint: "Edit name, username, email", onSelect: () => go("/account") },
    { label: "Security", hint: "Password & sign-in security", onSelect: () => go("/profile/security") },
    { label: "Activity", hint: "Sign-ins and account events", onSelect: () => go("/profile/activity") },
  ];

  if (user?.role === "admin") {
    items.push({
      label: "Administration",
      hint: "Feature controls & users",
      onSelect: () => go("/admin"),
    });
  }

  items.push({
    label: "Sign out",
    hint: undefined,
    onSelect: async () => {
      setOpen(false);
      const confirmed = window.confirm("Are you sure you want to sign out?");
      if (confirmed) {
        clearAuth();
        router.replace("/");
      }
    },
  });

  return (
    <div className="relative" data-profile-menu>
      <div
        onClick={() => setOpen(!open)}
        onMouseDown={(e) => e.stopPropagation()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setOpen(!open);
        }}
        aria-expanded={open}
        className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-800 text-xs font-bold text-white">
          {(user?.name || user?.email || "A").slice(0, 2).toUpperCase()}
        </span>
        <span className="truncate text-sm">{user?.name || user?.email || "Administrator"}</span>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="shrink-0"
        >
          <path d="M6 9l6 6 6-6" />
          <path d="M2 12l4 4 6-6" />
        </svg>
      </div>

      {open && (
        <div className={`absolute z-20 w-72 rounded-lg border border-gray-800 bg-gray-900 p-3 shadow-xl ${menuPlacement}`}>
          <div className="mb-2 border-b border-gray-800 px-1 pb-3">
            <p className="truncate text-sm font-semibold text-white">
              {user?.name || "KreatOS"}
            </p>
            <p className="truncate text-xs text-gray-500">
              {user?.username ? `@${user.username} · ` : ""}
              {user?.email || ""}
            </p>
            <span
              className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                user?.role === "admin"
                  ? "bg-blue-500/15 text-blue-300"
                  : "bg-gray-800 text-gray-400"
              }`}
            >
              {user?.role === "admin" ? "Administrator" : "User"}
            </span>
          </div>
          <div className="max-h-[min(70vh,24rem)] overflow-y-auto">
            {items.map((item, i) => (
              <button
                key={i}
                onClick={(e) => {
                  e.stopPropagation();
                  item.onSelect();
                }}
                className="flex w-full items-baseline justify-between gap-3 rounded-md px-1 py-2.5 text-left text-sm font-medium text-gray-200 hover:bg-gray-950 hover:text-white transition-colors"
              >
                <span>{item.label}</span>
                {item.hint ? <span className="truncate text-[10px] font-normal text-gray-600">{item.hint}</span> : null}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileDropdown;