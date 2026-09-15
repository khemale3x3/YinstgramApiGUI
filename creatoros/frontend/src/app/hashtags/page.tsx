"use client";

import InstagramOperations from "@/components/InstagramOperations";

export default function HashtagsPage() {
  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8"><h1 className="text-2xl font-bold tracking-tight text-white">Hashtags</h1><p className="mt-1 text-sm text-gray-400">Search public hashtag information and recent or top media through Instagram.</p><InstagramOperations mode="hashtags" /></div>
  );
}