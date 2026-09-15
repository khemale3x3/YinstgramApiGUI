"use client";

import TabbedModule from "@/components/TabbedModule";

export default function EngagementPage() {
  return (
    <TabbedModule
      featureKey="engagement"
      title="Engagement"
      subtitle="Comments, likes, followers and interactions. Off by default — analytics focus is recommended."
    />
  );
}