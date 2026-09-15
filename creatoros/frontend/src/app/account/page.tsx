"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Err, Input, PageHeader, Btn, Loader, Field } from "@/components/ui";
import { adminMe, updateProfile, type AdminUser } from "@/lib/api";

export default function AccountPage() {
  const router = useRouter();
  const [me, setMe] = useState<AdminUser | null>(null);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    adminMe()
      .then((data: AdminUser) => {
        setMe(data);
        setName(data.name ?? "");
        setUsername(data.username ?? "");
        setEmail(data.email ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load account"));
  }, []);

  async function save() {
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await updateProfile(name, username);
      setMe((m) => (m ? { ...m, name: updated.name, username: updated.username } : m));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setBusy(false);
    }
  }

  if (!me && !error) return <Loader />;

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Account Settings"
        subtitle="Update your display name and username. Your sign-in email is shown below for reference."
      />

      {error && <div className="mb-6"><Err message={error} /></div>}
      {saved && (
        <div className="mb-6 rounded-lg border border-emerald-800 bg-emerald-950/50 p-3 text-sm text-emerald-300">
          Profile updated.
        </div>
      )}

      <div className="grid gap-6">
        <Card title="Profile">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name">
              <Input value={name} onChange={setName} placeholder="Your display name" />
            </Field>
            <Field label="Username">
              <Input value={username} onChange={setUsername} placeholder="@username" />
            </Field>
            <Field label="Email">
              <Input value={email} onChange={() => {}} placeholder="Email" />
            </Field>
            <Field label="Role">
              <Input value={me?.role === "admin" ? "Administrator" : "User"} onChange={() => {}} />
            </Field>
          </div>
          {me?.username && me.username !== username ? (
            <p className="mt-3 text-xs text-amber-400">
              Changing your username will update the handle shown across the app.
            </p>
          ) : null}
        </Card>

        <Card title="Password">
          <p className="mb-4 text-sm text-gray-400">
            You can change your password from the security page.
          </p>
          <Btn onClick={() => router.push("/profile/security")}>
            Change password
          </Btn>
        </Card>

        <div className="flex justify-end">
          <Btn primary onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </Btn>
        </div>
      </div>
    </div>
  );
}