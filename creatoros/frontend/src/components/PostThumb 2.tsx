import type { CreatorPost } from "@/lib/api";
import { formatNumber } from "@/lib/api";

const TYPE_LABELS: Record<CreatorPost["media_type"], string> = {
  photo: "Photo",
  video: "Video",
  album: "Album",
  unknown: "",
};

export default function PostThumb({ post }: { post: CreatorPost }) {
  const type = TYPE_LABELS[post.media_type] ?? "";

  return (
    <a
      href={post.thumbnail_url ?? void 0}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative block aspect-square overflow-hidden rounded-lg border border-gray-800 bg-gray-900"
    >
      {post.thumbnail_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={post.thumbnail_url}
          alt={post.caption || `@post by ${post.shortcode}`}
          className="h-full w-full object-cover transition-transform group-hover:scale-105"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-xs text-gray-600">
          {type}
        </div>
      )}

      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3 pt-8">
        <p className="text-sm font-medium text-white">
          {formatNumber(post.likes)}
          <span className="mx-1.5 text-gray-400">·</span>
          {formatNumber(post.comments)}
          {post.plays > 0 ? (
            <>
              <span className="mx-1.5 text-gray-400">·</span>
              {formatNumber(post.plays)} plays
            </>
          ) : null}
        </p>
        <p className="text-xs text-gray-300">{post.caption || type}</p>
      </div>
    </a>
  );
}