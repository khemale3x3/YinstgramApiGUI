export default function StatCard({
  title,
  value,
  hint,
}: {
  title: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
      <p className="text-xs uppercase tracking-wider text-gray-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value || "-"}</p>
      {hint ? <p className="mt-1 text-xs text-gray-600">{hint}</p> : null}
    </div>
  );
}