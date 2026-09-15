"use client";

import { useState } from "react";
import { Card, Err, Input, PageHeader, Btn, Field } from "@/components/ui";
import { changePassword } from "@/lib/api";

export default function SecurityPage() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save() {
    setError("");
    setSaved(false);
    if (!current || !next) {
      setError("Enter your current and new password.");
      return;
    }
    if (next.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      setError("New password confirmation does not match.");
      return;
    }
    setBusy(true);
    try {
      await changePassword(current, next);
      setSaved(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to change password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Security"
        subtitle="Keep your account safe by updating your password regularly."
      />

      {error && <div className="mb-6"><Err message={error} /></div>}
      {saved && (
        <div className="mb-6 rounded-lg border border-emerald-800 bg-emerald-950/50 p-3 text-sm text-emerald-300">
          Password changed successfully.
        </div>
      )}

      <Card title="Change password">
        <div className="grid gap-4">
          <Field label="Current password">
            <Input
              type="password"
              value={current}
              onChange={setCurrent}
              placeholder="Enter current password"
            />
          </Field>
          <Field label="New password">
            <Input
              type="password"
              value={next}
              onChange={setNext}
              placeholder="At least 8 characters"
            />
          </Field>
          <Field label="Confirm new password">
            <Input
              type="password"
              value={confirm}
              onChange={setConfirm}
              placeholder="Re-enter new password"
            />
          </Field>
        </div>
        <div className="mt-5 flex justify-end">
          <Btn primary onClick={save} disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </Btn>
        </div>
      </Card>

      <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <h2 className="mb-2 text-sm font-semibold text-gray-200">Security tips</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-400">
          <li>Use a unique password you do not reuse elsewhere.</li>
          <li>Keep your password at least 8 characters long.</li>
          <li>Sign out from shared devices when you are done.</li>
          <li>Review recent sign-ins from your activity page.</li>
        </ul>
      </div>
    </div>
  );
}