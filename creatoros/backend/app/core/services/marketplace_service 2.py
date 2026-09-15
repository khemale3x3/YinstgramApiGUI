"""Marketplace use case: category browsing, discovery and saving creators.

Discovery runs a live Instagram account-search per subcategory and persists
non-private hits into the profile store with the subcategory as its category
label — so lists, Find Creators, matching and the creator detail page all read
the same stored records. Nothing here fabricates data: with no connected
account, the endpoints degrade and the UI explains it.
"""
from __future__ import annotations

from app.core.services.database_service import DatabaseService
from app.core.services.instagram_service import InstagramService

SUBCATEGORIES: list[dict] = [
    {"key": "ugc", "label": "UGC Creator", "search": "ugc creators"},
    {"key": "influencers", "label": "Influencer", "search": "influencer"},
    {"key": "digital", "label": "Digital Creator", "search": "digital creator"},
    {"key": "reel", "label": "Reel Creator", "search": "reel creator"},
    {"key": "blogger", "label": "Blogger", "search": "blogger"},
    {"key": "generic", "label": "Generic User", "search": ""},
]

_SPECIFIC_KEYS = [s["key"] for s in SUBCATEGORIES if s["key"] != "generic"]
_SPECIFIC_LABELS = [s["label"].lower() for s in SUBCATEGORIES if s["key"] != "generic"]


class MarketplaceService:
    def __init__(self, db: DatabaseService, instagram: InstagramService | None = None):
        self._db = db
        self._instagram = instagram

    # ------------------------------------------------------------------ lists
    def categories(self) -> list[dict]:
        out: list[dict] = []
        total = self._db.count()
        other = 0
        for sub in SUBCATEGORIES:
            if sub["key"] == "generic":
                count = max(0, total - other)
            else:
                count = self._db.count_by_category(sub["label"])
                other += count
            out.append({"key": sub["key"], "label": sub["label"], "count": count})
        return out

    def _label(self, key: str) -> str | None:
        for sub in SUBCATEGORIES:
            if sub["key"] == key:
                return sub["label"]
        return None

    def list_creators(
        self,
        key: str,
        limit: int = 50,
        query: str = "",
        min_followers: int = 0,
        verified: bool = False,
        sort: str = "followers",
    ) -> list[dict]:
        label = self._label(key)
        if label is None:
            return []
        if key == "generic":
            rows = self._db.recent(max(limit, 50) * 4)
            rows = [r for r in rows if (r.get("category") or "").lower() not in _SPECIFIC_LABELS]
            rows = rows[:limit]
        else:
            rows = self._db.list_by_category(label, limit)
        normalized_query = query.strip().lower()
        if normalized_query:
            rows = [
                row for row in rows
                if normalized_query in str(row.get("username") or "").lower()
                or normalized_query in str(row.get("full_name") or "").lower()
                or normalized_query in str(row.get("biography") or "").lower()
            ]
        if min_followers > 0:
            rows = [row for row in rows if int(row.get("followers") or 0) >= min_followers]
        if verified:
            rows = [row for row in rows if bool(row.get("is_verified"))]
        if sort == "followers":
            rows.sort(key=lambda row: int(row.get("followers") or 0), reverse=True)
        elif sort == "media":
            rows.sort(key=lambda row: int(row.get("media_count") or 0), reverse=True)
        elif sort == "recent":
            rows.sort(key=lambda row: str(row.get("scraped_at") or ""), reverse=True)
        for row in rows[:limit]:
            row["subcategory"] = key
            row.setdefault("profile_pic_url", "")
        return rows

    # -------------------------------------------------------------- favorites
    def is_favorited(self, username: str) -> bool:
        """Check if a creator is in the saved/favorites list."""
        if self._db is None:
            return False
        try:
            return self._db.favorited(username) > 0
        except Exception:
            return False

    def favorite(self, username: str) -> dict:
        """Save a creator to the favorites/saved list."""
        if self._db is None:
            raise ValueError("Database not configured")
        return self._db.favorite(username)

    def unfavorite(self, username: str) -> dict:
        """Remove a creator from the favorites/saved list."""
        if self._db is None:
            raise ValueError("Database not configured")
        return self._db.unfavorite(username)

    # -------------------------------------------------------------- discovery
    def discover(self, key: str, limit: int = 20) -> dict:
        if key == "generic":
            raise ValueError("Generic User has no search term; save creators to populate it")
        sub = next((s for s in SUBCATEGORIES if s["key"] == key), None)
        if sub is None:
            raise ValueError(f"Unknown subcategory {key!r}")
        if self._instagram is None:
            raise ValueError("Instagram engine is not connected for this market")
        fetch = max(limit, 20) * 2
        try:
            matches = self._instagram.search_creators(sub["search"], fetch)
        except Exception as exc:  # noqa: BLE001 - surface instagrapi failures cleanly
            raise ValueError(
                f"Could not reach Instagram for '{sub['search']}': {exc}"
            ) from exc
        saved = 0
        skipped = []
        for m in matches:
            if m.get("is_private"):
                skipped.append(m.get("username"))
                continue
            if not m.get("username"):
                continue
            record = {
                **m,
                "category": sub["label"],
                "url": f"https://www.instagram.com/{m['username']}/",
            }
            if self._db.upsert(record):
                saved += 1
        return {
            "subcategory": sub,
            "found": len(matches),
            "saved": saved,
            "skipped_private": len(skipped),
            "creators": self.list_creators(key, limit),
            "category_counts": self.categories(),
        }

    # ------------------------------------------------------------------ save
    def save(self, record: dict) -> dict:
        cleaned = {k: v for k, v in (record or {}).items() if v is not None}
        self._db.upsert(cleaned)
        return cleaned