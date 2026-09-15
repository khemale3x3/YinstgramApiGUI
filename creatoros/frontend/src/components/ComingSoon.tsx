"use client";

export default function ComingSoon({ title, blurb }: { title: string; blurb: string }) {
  return (
    <div className="max-w-3xl mx-auto p-12">
      <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
      <p className="mt-2 text-sm text-gray-400">{blurb}</p>
      <div className="mt-8 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
        <p className="text-sm text-gray-500">
          This module is enabled in Administration → Feature Controls, but its page
          ships in the next build pass.
        </p>
      </div>
    </div>
  );
}