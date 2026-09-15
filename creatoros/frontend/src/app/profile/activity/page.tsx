"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Err, Loader, Empty } from "@/components/ui";
import { getMyActivity, formatWhen, type ActivityEntry } from "@/lib/api";

export default function ActivityPage() {
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyActivity()
      .then((res) => setActivities(res.entries || []))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load activity"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Activity"
        subtitle="Recent audit events and connection activity on your account."
      />

      {error && <div className="mb-6"><Err message={error} /></div>}

      <Card title="Recent activity">
        {loading ? (
          <Loader />
        ) : activities.length === 0 ? (
          <Empty label="No activity recorded yet." />
        ) : (
          <ul className="divide-y divide-gray-800">
            {activities.map((a, i) => (
              <li key={i} className="flex items-start gap-4 py-3">
                <span
                  className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                    a.kind === "connection" ? "bg-blue-500" : "bg-emerald-500"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-200">
                    <span className="font-medium capitalize">{a.action || "event"}</span>
                    {a.target ? <span className="text-gray-500"> on {a.target}</span> : null}
                  </p>
                  {a.detail ? <p className="truncate text-xs text-gray-500">{a.detail}</p> : null}
                </div>
                <span className="shrink-0 text-xs text-gray-500">
                  {a.created_at ? formatWhen(a.created_at) : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}