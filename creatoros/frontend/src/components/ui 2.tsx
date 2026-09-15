"use client";

import type { ReactNode } from "react";

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
      {subtitle ? <p className="mt-1 text-sm text-gray-400">{subtitle}</p> : null}
    </div>
  );
}

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-gray-800 bg-gray-900/50 p-5 ${className}`}>
      {title ? <h2 className="mb-4 text-sm font-semibold text-gray-200">{title}</h2> : null}
      {children}
    </div>
  );
}

export function Btn({
  children,
  onClick,
  disabled,
  primary,
  danger,
  size = "md",
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  primary?: boolean;
  danger?: boolean;
  size?: "sm" | "md";
  type?: "button" | "submit";
  className?: string;
}) {
  const tone = danger
    ? "bg-red-600 text-white hover:bg-red-500"
    : primary
      ? "bg-white text-black hover:bg-gray-200"
      : "bg-gray-800 text-gray-200 hover:bg-gray-700 border border-gray-700";
  const pad = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed ${tone} ${pad} ${className}`}
    >
      {children}
    </button>
  );
}

export function Input({
  value,
  onChange,
  placeholder,
  type = "text",
  className = "",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`rounded-lg border border-gray-700 bg-gray-950 px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600 ${className}`}
    />
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-gray-400">{label}</span>
      {children}
    </label>
  );
}

export function StatusBadge({ label, tone = "gray" }: { label: string; tone?: "gray" | "green" | "amber" | "red" | "blue" }) {
  const tones: Record<string, string> = {
    gray: "bg-gray-500/15 text-gray-300 border-gray-600",
    green: "bg-emerald-500/15 text-emerald-300 border-emerald-700",
    amber: "bg-amber-500/15 text-amber-300 border-amber-700",
    red: "bg-red-500/15 text-red-300 border-red-700",
    blue: "bg-blue-500/15 text-blue-300 border-blue-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]} capitalize`}>
      {label}
    </span>
  );
}

export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-800">
      <div
        className="h-full rounded-full bg-emerald-500 transition-all"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export function Loader() {
  return <p className="py-6 text-center text-sm text-gray-500">Loading…</p>;
}

export function Err({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
      {message}
    </div>
  );
}

export function Empty({ label = "Nothing here yet." }: { label?: string }) {
  return <p className="py-6 text-center text-sm text-gray-500">{label}</p>;
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="mt-4 flex items-center justify-between border-t border-gray-800 pt-3 text-xs text-gray-500">
      <span>Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}</span>
      <div className="flex items-center gap-1">
        <button type="button" onClick={() => onPage(page - 1)} disabled={page === 1} className="rounded border border-gray-700 px-2 py-1 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40">Previous</button>
        <span className="px-2 text-gray-300">{page} / {pages}</span>
        <button type="button" onClick={() => onPage(page + 1)} disabled={page === pages} className="rounded border border-gray-700 px-2 py-1 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}