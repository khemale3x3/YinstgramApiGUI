"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import {
  formatNumber,
  formatWhen,
  getCreator,
  getCreatorPosts,
  getProfile,
  listCampaigns,
  marketplaceSave,
  type Campaign,
  type CreatorPost,
  type CreatorProfile,
  type ProfileRecord,
} from "@/lib/api";

type Tab =
  | "overview"
  | "posts"
  | "reels"
  | "stories"
  | "analytics"
  | "audience"
  | "campaigns"
  | "history";

const TABS: Array<{ key: Tab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "posts", label: "Posts" },
  { key: "reels", label: "Reels" },
  { key: "stories", label: "Stories" },
  { key: "analytics", label: "Analytics" },
  { key: "audience", label: "Audience" },
  { key: "campaigns", label: "Campaigns" },
  { key: "history", label: "History" },
];

export default function CreatorDetailPage() {
  const params = useParams<{ creatorId: string }>();
  const username = decodeURIComponent((params?.creatorId ?? "").toString());

  const [saved, setSaved] = useState<ProfileRecord | null>(null);
  const [live, setLive] = useState<CreatorProfile | null>(null);
  const [posts, setPosts] = useState<CreatorPost[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  useEffect(() => {
    if (!username) return;
    let alive = true;
    getProfile(username)
      .then((p) => alive && setSaved(p))
      .catch(() => {});
    listCampaigns()
      .then((d) => alive && setCampaigns(d.campaigns))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [username]);

  async function analyzeLive() {
    const query = username.replace(/^@/, "");
    if (!query) return;
    setLoading(true);
    setError("");
    setLive(null);
    setPosts([]);
    try {
      const [creator, recent] = await Promise.all([
        getCreator(query),
        getCreatorPosts(query, 12),
      ]);
      setLive(creator);
      setPosts(recent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Live analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile() {
    if (!profile) return;
    setSaving(true);
    setActionMsg("");
    try {
      await marketplaceSave({
        username: username.replace(/^@/, ""),
        full_name: "full_name" in profile ? profile.full_name ?? "" : saved?.full_name ?? "",
        biography,
        category,
        followers,
        following,
        media_count: mediaCount,
        is_private: "is_private" in profile ? profile.is_private ?? false : saved?.is_private ?? false,
        is_verified: isVerified,
        profile_pic_url:
          "profile_pic_url" in profile
            ? profile.profile_pic_url ?? ""
            : saved?.profile_pic_url ?? "",
        url: `https://www.instagram.com/${username.replace(/^@/, "")}/`,
      });
      setIsSaved(true);
      setActionMsg("Saved to marketplace");
      getProfile(username)
        .then(setSaved)
        .catch(() => {});
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const profile = live ?? saved;
  if (!profile) {
    return (
      <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold tracking-tight text-white">{username}</h1>
        <p className="mt-1 text-sm text-gray-400">
          Creator profile — overview, posts, analytics and campaign placement.
        </p>
        {error && (
          <div className="mt-6 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
            {error}
          </div>
        )}
        <div className="mt-8 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
          <p className="text-sm text-gray-400">
            No stored data for this creator yet.
          </p>
          <button
            onClick={analyzeLive}
            disabled={loading}
            className="mt-4 rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black disabled:opacity-50"
          >
            {loading ? "Analyzing…" : "Fetch live profile & posts"}
          </button>
        </div>
      </div>
    );
  }

  const followers =
    "followers" in profile ? profile.followers : saved?.followers ?? 0;
  const following =
    "following" in profile ? profile.following : saved?.following ?? 0;
  const mediaCount =
    "media_count" in profile ? profile.media_count : saved?.media_count ?? 0;
  const isVerified =
    ("is_verified" in profile && profile.is_verified) ?? saved?.is_verified ?? false;
  const fullName = profile.full_name || `@${username}`;
  const category = profile.category || (saved?.category ?? "");
  const biography = profile.biography || saved?.biography || "";

  const reels = posts.filter((p) => p.media_type === "video");
  const avgLikes = posts.length
    ? Math.round(posts.reduce((sum, p) => sum + p.likes, 0) / posts.length)
    : 0;
  const avgComments = posts.length
    ? Math.round(posts.reduce((sum, p) => sum + p.comments, 0) / posts.length)
    : 0;
  const engagement =
    followers > 0 && avgLikes > 0 ? (avgLikes / followers) * 100 : null;
  const profilePicUrl =
    "profile_pic_url" in profile
      ? profile.profile_pic_url ?? ""
      : saved?.profile_pic_url ?? "";
  const location = (profile as { location?: string }).location ?? "";

  const campaignsWith = campaigns.filter((c) => (c.matched ? true : false));

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center gap-5 rounded-2xl border border-gray-800 bg-gray-900/40 p-6">
        {profilePicUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={profilePicUrl}
            alt=""
            className="h-20 w-20 shrink-0 rounded-full border border-gray-800 object-cover"
          />
        ) : (
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border border-gray-800 bg-gray-950 text-2xl font-bold text-gray-600">
            {(fullName || "@").slice(0, 1).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-2xl font-bold tracking-tight text-white">
            {fullName} {isVerified ? "✓" : ""}
          </h1>
          <p className="mt-1 truncate text-sm text-gray-400">
            @{username}
            {category ? ` · ${category}` : ""}
            {location ? ` · ${location}` : ""}
          </p>
          {biography ? (
            <p className="mt-2 line-clamp-2 max-w-3xl text-sm text-gray-500">{biography}</p>
          ) : null}
          {actionMsg && <p className="mt-2 text-xs text-blue-300">{actionMsg}</p>}
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
          <button
            onClick={analyzeLive}
            disabled={loading}
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
          <button
            onClick={saveProfile}
            disabled={saving || isSaved}
            className="rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800 disabled:opacity-50"
          >
            {isSaved ? "Saved ✓" : saving ? "Saving…" : "Save"}
          </button>
          <a
            href={`https://www.instagram.com/${username}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-900"
          >
            Open →
          </a>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Followers" value={formatNumber(followers)} />
        <StatCard title="Following" value={formatNumber(following)} />
        <StatCard title="Posts" value={formatNumber(mediaCount)} />
        <StatCard
          title="Engagement"
          value={engagement === null ? "—" : `${engagement.toFixed(1)}%`}
        />
      </div>

      <div className="mt-8 flex flex-wrap gap-2 border-b border-gray-800 pb-px">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={
              tab === t.key
                ? "rounded-t-lg border-b-2 border-white px-3 py-2 text-sm font-medium text-white"
                : "rounded-t-lg border-b-2 border-transparent px-3 py-2 text-sm text-gray-500 hover:text-gray-300"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "overview" && (
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
                <h2 className="text-sm font-semibold text-gray-200">Performance</h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Row label="Followers" value={formatNumber(followers)} />
                  <Row
                    label="Engagement"
                    value={engagement === null ? "—" : `${engagement.toFixed(1)}%`}
                  />
                  <Row label="Avg Likes" value={formatNumber(avgLikes)} />
                  <Row label="Avg Comments" value={formatNumber(avgComments)} />
                </div>
              </div>
              <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
                <h2 className="text-sm font-semibold text-gray-200">Profile</h2>
                <dl className="mt-4 flex flex-col gap-3 text-sm">
                  <Row label="Username" value={`@${username}`} />
                  <Row label="Name" value={fullName} />
                  <Row label="Category" value={category || "—"} />
                  <Row label="Verified" value={isVerified ? "Yes" : "No"} />
                  <Row label="First collected" value={saved ? formatWhen(saved.scraped_at) : "—"} />
                </dl>
              </div>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-200">Recent content</h2>
                <button
                  onClick={() => setTab("posts")}
                  className="text-xs text-blue-400 hover:underline"
                >
                  View all →
                </button>
              </div>
              {posts.length === 0 ? (
                <p className="mt-3 text-sm text-gray-500">
                  No posts collected yet. Use <b>Analyze</b> to pull the latest content.
                </p>
              ) : (
                <div className="mt-4 grid grid-cols-3 md:grid-cols-6 gap-3">
                  {posts.slice(0, 6).map((post) => (
                    <a
                      key={post.pk}
                      href={`https://www.instagram.com/p/${post.shortcode}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group overflow-hidden rounded-lg border border-gray-800 bg-gray-950"
                    >
                      <div className="aspect-square w-full overflow-hidden">
                        {post.thumbnail_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={post.thumbnail_url}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full items-center justify-center text-xs text-gray-600">
                            ♥ {formatNumber(post.likes)}
                          </div>
                        )}
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "posts" && <PostsGrid posts={posts} />}
        {tab === "reels" && <PostsGrid posts={reels} empty={`@${username} has no collected reels yet.`} />}

        {tab === "stories" && (
          <EmptyPanel
            title="Stories"
            body="Story scraping requires a connected Instagram account session with an active cookie. Once a session is linked, daily story highlights will appear here."
          />
        )}

        {tab === "analytics" && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard title="Avg Likes" value={formatNumber(avgLikes)} />
            <StatCard title="Avg Comments" value={formatNumber(avgComments)} />
            <StatCard title="Media Count" value={formatNumber(mediaCount)} />
            <StatCard
              title="Engagement"
              value={engagement === null ? "—" : `${engagement.toFixed(1)}%`}
            />
            {posts.length === 0 && (
              <p className="col-span-full mt-2 text-sm text-gray-500">
                Run a post collection to unlock per-post analytics.
              </p>
            )}
          </div>
        )}

        {tab === "audience" && (
          <EmptyPanel
            title="Audience"
            body="Audience demographics, active regions and follower growth require historical scrapes over time. This panel fills in as the creator is analyzed and re-collected."
          />
        )}

        {tab === "campaigns" && (
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-200">Campaign placement</h2>
              <Link href="/campaigns" className="text-xs text-blue-400 hover:underline">
                Manage campaigns →
              </Link>
            </div>
            {campaignsWith.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">
                @{username} is not yet part of any campaign. Create a campaign and run
                matching to shortlist them.
              </p>
            ) : (
              <div className="mt-4 flex flex-col gap-2">
                {campaignsWith.map((c) => (
                  <Link
                    key={c.id}
                    href={`/campaigns/${c.id}`}
                    className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-950 px-4 py-3 text-sm hover:border-gray-700"
                  >
                    <span className="text-gray-200">{c.name}</span>
                    <span className="text-xs text-gray-500">
                      {c.matched} matched · {c.status}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "history" && (
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <h2 className="text-sm font-semibold text-gray-200">Collection history</h2>
            {posts.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">
                No post collection runs recorded yet for @{username}.
              </p>
            ) : (
              <div className="mt-4 flex flex-col gap-2">
                {posts.map((p) => (
                  <div key={p.pk} className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-950 px-4 py-2 text-sm">
                    <span className="truncate text-gray-300">
                      {p.media_type} · {formatNumber(p.likes)} likes
                    </span>
                    <span className="shrink-0 text-xs text-gray-600">
                      {formatWhen(p.taken_at)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-gray-500">{label}</dt>
      <dd className="truncate text-gray-200">{value}</dd>
    </div>
  );
}

function PostsGrid({ posts, empty }: { posts: CreatorPost[]; empty?: string }) {
  if (posts.length === 0) {
    return (
      <EmptyPanel
        title="Posts"
        body={empty ?? "No posts collected yet. Use Refresh live to pull the latest posts."}
      />
    );
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {posts.map((post) => (
        <a
          key={post.pk}
          href={`https://www.instagram.com/p/${post.shortcode}/`}
          target="_blank"
          rel="noopener noreferrer"
          className="group overflow-hidden rounded-xl border border-gray-800 bg-gray-900/50"
        >
          <div className="aspect-square w-full overflow-hidden bg-gray-950">
            {post.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={post.thumbnail_url}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-gray-600">
                no thumbnail
              </div>
            )}
          </div>
          <div className="flex items-center justify-between px-3 py-2 text-xs text-gray-400">
            <span>♥ {formatNumber(post.likes)}</span>
            <span className="capitalize">{post.media_type}</span>
          </div>
        </a>
      ))}
    </div>
  );
}

function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
      <p className="text-sm font-medium text-gray-300">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">{body}</p>
    </div>
  );
}