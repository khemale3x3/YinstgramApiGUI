"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminMe, clearAuth, formatWhen, type AdminUser, type MenuTree } from "@/lib/api";

export default function ProfilePage() {
  const router = useRouter();
  const [me, setMe] = useState<AdminUser | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    adminMe()
      .then((me: AdminUser) => setMe(me))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"));
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
        {error}
      </div>
    );
  }

  if (!me) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-lg text-gray-400">Loading profile…</p>
      </div>
    );
  }

  const role = me.role || "user";
  const isAdmin = role === "admin";
  const features = (me.features || []).filter((f) => f.enabled);
  const menus: MenuTree = me.menus || {};

  // Count every rendered menu item (submenu entries included).
  const menuCount = Object.values(menus).reduce((n, items) => n + items.length, 0);
  const featureCount = features.length;

  const initials =
    (me.name || "U")
      .split(" ")
      .map((n: string) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "U";

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="h-14 w-14 rounded-full bg-gray-800/80 flex items-center justify-center text-xl font-bold text-white">
            {initials}
          </span>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white">
              {me.name || "KreatOS Profile"}
            </h1>
            <p className="text-gray-400 mt-1">
              {me.username ? `@${me.username} · ` : ""}
              {me.email}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-sm text-right text-gray-400">
            <p>
              Role:{" "}
              <span className={isAdmin ? "text-blue-300" : "text-gray-200"}>
                {isAdmin ? "Administrator" : "User"}
              </span>
            </p>
            <p>Features enabled: {featureCount}</p>
            <p>Menu items accessible: {menuCount}</p>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              me.status === "active"
                ? "border-emerald-700 bg-emerald-500/15 text-emerald-300"
                : "border-red-700 bg-red-500/15 text-red-300"
            }`}
          >
            {me.status || "active"}
          </span>
        </div>
      </div>

      {/* Profile Overview Section */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {/* Profile Information Card */}
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Profile</h2>
          <div className="mt-3 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Full name</p>
                <p className="text-white font-medium">{me.name || "—not set—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Username</p>
                <p className="text-white font-medium">@{me.username || "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Email</p>
                <p className="text-white font-medium">{me.email || "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Account status</p>
                <span className={me.status === "active" ? "bg-green-600/20 text-green-400 text-xs rounded px-2" : "bg-red-600/20 text-red-400 text-xs rounded px-2"}>
                  {me.status || "active"}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-500">Date joined</p>
                <p className="text-gray-400 text-sm">{me.created_at ? formatWhen(me.created_at) : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Last login</p>
                <p className="text-gray-400 text-sm">{me.last_login ? formatWhen(me.last_login) : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Last activity</p>
                <p className="text-gray-400 text-sm">{me.last_activity ? formatWhen(me.last_activity) : "—"}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Administrator Information Card (admin only) */}
        {isAdmin ? (
          <div>
            <h2 className="text-sm font-semibold text-gray-200">Administrator Information</h2>
            <div className="mt-3 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Role</p>
                  <p className="text-white font-medium">Admin</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Permission level</p>
                  <p className="text-white font-medium">Full control</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Users managed</p>
                  <p className="text-gray-400 text-sm">{me.users_managed || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Assigned projects</p>
                  <p className="text-gray-400 text-sm">{me.assigned_projects?.length || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Instagram accounts</p>
                  <p className="text-gray-400 text-sm">{me.instagram_accounts?.length || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Permissions</p>
                  <p className="text-gray-400 text-sm">{me.permissions?.length || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Enabled features</p>
                  <p className="text-gray-400 text-sm">{featureCount}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Accessible menu items</p>
                  <p className="text-gray-400 text-sm">{menuCount}</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <h2 className="text-sm font-semibold text-gray-200">Your Access</h2>
            <div className="mt-3 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <p className="mb-3 text-xs text-gray-500">
                The features enabled for your account. Administration and system
                tools are reserved for the admin console.
              </p>
              <div className="flex flex-wrap gap-2">
                {features.length === 0 && (
                  <p className="text-sm text-gray-500">No modules enabled yet.</p>
                )}
                {features.map((f) => (
                  <span
                    key={f.key}
                    className="rounded-full border border-gray-800 bg-gray-950 px-3 py-1 text-xs text-gray-300"
                  >
                    {f.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Member / Plan Card */}
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Membership</h2>
          <div className="mt-3 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Email verified</p>
                <p className="text-emerald-400 text-sm font-medium">Yes</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Account type</p>
                <p className="text-white text-sm">{isAdmin ? "Administrator" : "Standard"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Date joined</p>
                <p className="text-gray-400 text-sm">{me.created_at ? formatWhen(me.created_at) : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Last login</p>
                <p className="text-gray-400 text-sm">{me.last_login ? formatWhen(me.last_login) : "—"}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Profile Actions Section */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-gray-200">Profile Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
          <Link
            href="/account"
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900 transition-colors text-center"
          >
            Edit Profile
          </Link>
          <Link
            href="/profile/security"
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900 transition-colors text-center"
          >
            Change Password
          </Link>
          <Link
            href="/profile/security"
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900 transition-colors text-center"
          >
            Security Settings
          </Link>
          <Link
            href="/profile/activity"
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900 transition-colors text-center"
          >
            View Activity
          </Link>
        </div>
      </div>

      {/* Sign Out Button */}
      <div className="mt-8">
        <button
          onClick={() => {
            if (window.confirm("Are you sure you want to sign out?")) {
              clearAuth();
              router.replace("/");
            }
          }}
          className="rounded-lg border border-red-700 px-4 py-2 text-sm text-red-400 hover:bg-red-900/20 transition-colors w-full"
          aria-label="Sign out"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}