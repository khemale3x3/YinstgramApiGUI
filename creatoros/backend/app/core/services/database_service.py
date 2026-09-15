from __future__ import annotations
from pathlib import Path

from app.core.ports.database import DatabasePort


class DatabaseService:
    """Use case: query the metadata database and drive SQL Server ingest."""

    def __init__(self, local: DatabasePort | None, remote: DatabasePort | None):
        self._local = local
        self._remote = remote

    def status(self) -> dict:
        return {
            "local": self._local.status() if self._local else {"available": False},
            "remote": self._remote.status() if self._remote else {"available": False},
        }

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        return self._local.search_profiles(query, limit, offset)

    def search_count(self, query: str) -> int | None:
        if self._local is None or not self._local.available():
            return None
        try:
            return self._local.count_search(query)
        except NotImplementedError:
            return None

    def get_profile(self, username: str) -> dict | None:
        if self._local is None or not self._local.available():
            return None
        return self._local.get_profile(username)

    def count(self) -> int:
        if self._local is None or not self._local.available():
            return 0
        return self._local.count_profiles()

    def recent(self, limit: int = 20) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        return self._local.list_recent(limit)

    def top(self, limit: int = 10, offset: int = 0) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        return self._local.top_profiles(limit, offset)

    def upsert(self, record: dict) -> bool:
        if self._local is None or not self._local.available():
            return False
        try:
            return bool(self._local.upsert_profile(record))
        except Exception:
            return False

    def list_by_category(self, category: str, limit: int = 50) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        try:
            return self._local.search_profiles_by_category(category, limit)
        except Exception:
            return []

    def count_by_category(self, category: str) -> int:
        if self._local is None or not self._local.available():
            return 0
        try:
            return int(self._local.count_profiles_by_category(category) or 0)
        except Exception:
            return 0

    def growth(self, days: int = 14) -> list[dict]:
        """Daily first-seen profile counts for the dashboard growth series."""
        if self._local is None or not self._local.available():
            return []
        try:
            return self._local.profile_growth(days)
        except Exception:
            return []

    def views(self) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        try:
            return self._local.list_views() or []
        except Exception:
            return []

    def tables(self) -> list[dict]:
        if self._local is None or not self._local.available():
            return []
        try:
            return self._local.list_tables() or []
        except Exception:
            return []

    def ingest(self, keylist_path: str | Path, on_event=None, table: str | None = None) -> dict:
        if self._remote is None:
            raise ValueError("SQL Server not configured")
        return self._remote.ingest_from_keylist(str(keylist_path), on_event=on_event, table=table)