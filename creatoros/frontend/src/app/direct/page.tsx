"use client";

import TabbedModule from "@/components/TabbedModule";

export default function DirectPage() {
  return (
    <TabbedModule
      featureKey="direct"
      title="Direct"
      subtitle="Inbox, conversations, messages, group threads and reactions. Off by default."
    />
  );
}