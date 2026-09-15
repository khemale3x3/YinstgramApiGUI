"""Use case: dashboard control-center aggregates.

Collects lightweight counters from the stores the admin plane already owns —
jit cold reads only (a handful of COUNT / LIMIT queries), suitable for a
5-second polling loop in the UI.
"""
from __future__ import annotations

from app.core.domain.job import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from app.core.ports.admin import AdminStorePort
from app.core.ports.database import DatabasePort
from app.core.ports.job_store import JobStorePort
from app.core.ports.storage import StoragePort


class DashboardService:
    def __init__(
        self,
        jobs: JobStorePort,
        profiles: DatabasePort,
        sessions,                     # SessionService: exposes .counts()
        storage: StoragePort | None,
        admin: AdminStorePort,
        campaigns=None,               # CampaignStorePort (optional)
    ):
        self._jobs = jobs
        self._profiles = profiles
        self._sessions = sessions
        self._storage = storage
        self._admin = admin
        self._campaigns = campaigns

    def stats(self) -> dict:
        counts = self._jobs.count_by_status()
        session_counts = self._sessions.counts() if hasattr(self._sessions, "counts") else {}
        storage_ok = False
        try:
            storage_ok = bool(self._storage and self._storage.available())
        except Exception:
            storage_ok = False

        try:
            creators = self._profiles.count_profiles()
        except Exception:
            creators = 0
        try:
            posts_analyzed = self._profiles.sum_media_count()
        except Exception:
            posts_analyzed = 0

        campaigns: dict = {}
        if self._campaigns is not None:
            try:
                campaigns = self._campaigns.campaign_stats()
            except Exception:
                campaigns = {}

        return {
            "creators": creators,
            "posts_analyzed": posts_analyzed,
            "campaigns": {
                "total": campaigns.get("total", 0),
                "matches": campaigns.get("matches", 0),
                "by_status": campaigns.get("by_status", {}),
            },
            "accounts": {
                "cookie_total": session_counts.get("cookie_total", 0),
                "cookie_active": session_counts.get("cookie_active", 0),
                "cookie_backup": session_counts.get("cookie_backup", 0),
                "instagrapi": session_counts.get("instagrapi", 0),
                "total": session_counts.get("total", 0),
            },
            "storage_available": storage_ok,
            "jobs": {
                "running": counts.get(STATUS_RUNNING, 0),
                "failed": counts.get(STATUS_FAILED, 0),
                "completed": counts.get(STATUS_SUCCEEDED, 0),
                "cancelled": counts.get(STATUS_CANCELLED, 0),
                "queued": max(0, sum(counts.values()) - counts.get(STATUS_RUNNING, 0)),
            },
        }

    def top_creators(self, limit: int = 5) -> list[dict]:
        try:
            rows = self._profiles.top_profiles(limit=limit)
        except Exception:
            return []
        n = len(rows)
        out = []
        for i, p in enumerate(rows):
            score = round(100 * (n - i) / n if n else 0, 1)
            if p.get("is_verified"):
                score = min(100.0, score + 5)
            if p.get("category"):
                score = min(100.0, score + 3)
            out.append(
                {
                    "username": p.get("username"),
                    "full_name": p.get("full_name") or "",
                    "followers": p.get("followers") or 0,
                    "following": p.get("following") or 0,
                    "media_count": p.get("media_count") or 0,
                    "category": p.get("category") or "",
                    "profile_pic_url": p.get("profile_pic_url") or "",
                    "score": score,
                }
            )
        return out

    def discovery(self, limit: int = 20) -> dict:
        """Creator Discovery panel: totals, categories and top candidates."""
        rows: list[dict] = []
        total = 0
        try:
            rows = self._profiles.top_profiles(limit=limit)
            total = self._profiles.count_profiles()
        except Exception:
            pass
        categories: dict[str, int] = {}
        for p in rows:
            category = (p.get("category") or "").strip() or "uncategorized"
            categories[category] = categories.get(category, 0) + 1
        top_categories = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return {
            "total": total,
            "recent": len(rows),
            "categories": [{"name": name, "count": count} for name, count in top_categories],
            "top_candidates": self.top_creators(limit=limit),
        }

    def recent_activity(self, limit: int = 8) -> list[dict]:
        """Most recent audit entries, newest first."""
        try:
            entries = self._admin.list_audit(limit=limit)
        except Exception:
            return []
        return [
            {
                "time": e.created_at,
                "actor": e.user,
                "action": e.action,
                "target": e.target,
                "detail": e.detail,
            }
            for e in entries
        ]

    def growth(self, days: int = 14) -> list[dict]:
        """Creator Growth series: daily first-seen profile counts."""
        try:
            return self._profiles.profile_growth(days=days) or []
        except Exception:
            return []

    def snapshot(self) -> dict:
        return {
            "stats": self.stats(),
            "top_creators": self.top_creators(),
            "discovery": self.discovery(),
            "recent_activity": self.recent_activity(),
            "growth": self.growth(days=14),
        }