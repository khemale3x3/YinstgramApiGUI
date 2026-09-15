"use client";

import InstagramOperations from "@/components/InstagramOperations";

export default function PublishingPage() {
  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8"><h1 className="text-2xl font-bold tracking-tight text-white">Publishing</h1><p className="mt-1 text-sm text-gray-400">Publish photos, videos, and carousels through the authenticated Instagram session.</p><InstagramOperations mode="publishing" /></div>
  );
}