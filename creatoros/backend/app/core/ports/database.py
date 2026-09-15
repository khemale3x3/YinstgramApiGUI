from __future__ import annotations
from abc import ABC, abstractmethod


class DatabasePort(ABC):
    """Secondary port for profile metadata and ingest targets.

    Two implementations ship with CreatorOS:
    - local SQLite scraper store  (search/count/recent over scraped profiles)
    - SQL Server adapter         (ingest into dbo.prodmauploadvakodata)

    Methods return sensible defaults / raise NotImplementedError where a
    backend does not provide them, and the services degrade gracefully.
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def available(self) -> bool:
        """Whether the backend is reachable/configured."""

    def status(self) -> dict:
        return {"name": self.name, "available": self.available()}

    def save_profile(self, username: str, url: str, profile_info: dict, post_info: dict, stats: dict | None = None) -> bool:
        raise NotImplementedError

    def search_profiles(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        raise NotImplementedError

    def count_search(self, query: str) -> int | None:
        """Count of profiles matching the search predicate (for pagination)."""
        raise NotImplementedError

    def count_profiles(self) -> int:
        raise NotImplementedError

    def sum_media_count(self) -> int:
        """Sum of all known media counts (approximate 'posts analyzed')."""
        raise NotImplementedError

    def top_profiles(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """Profiles ordered by followers, per-composition trending data."""
        raise NotImplementedError

    def list_recent(self, limit: int = 20) -> list[dict]:
        raise NotImplementedError

    def get_profile(self, username: str) -> dict | None:
        raise NotImplementedError

    def upsert_profile(self, record: dict) -> bool:
        """Upsert a typed profile record (marketplace save/discovery)."""
        raise NotImplementedError

    def count_profiles_by_category(self, category: str) -> int:
        raise NotImplementedError

    def search_profiles_by_category(self, category: str, limit: int = 50) -> list[dict]:
        """Profiles whose category matches the given label (case-insensitive)."""
        raise NotImplementedError

    def favorited(self, username: str) -> int:
        """Return 1 if username is in creator_favorites, else 0."""
        raise NotImplementedError

    def favorite(self, username: str) -> dict:
        """Add username to creator_favorites. Returns dict with saved status."""
        raise NotImplementedError

    def unfavorite(self, username: str) -> dict:
        """Remove username from creator_favorites. Returns dict with saved status."""

    def list_lists(self) -> list[dict]:
        """Return all creator lists with name, creator and creation date."""
        raise NotImplementedError

    def create_list(self, name: str, created_by: str = "admin") -> dict:
        """Create a new creator list. Returns dict with created status."""
        raise NotImplementedError

    def add_to_list(self, list_name: str, username: str) -> dict:
        """Add a creator to a list. Returns dict with added status."""
        raise NotImplementedError

    def remove_from_list(self, list_name: str, username: str) -> dict:
        """Remove a creator from a list. Returns dict with removed status."""
        raise NotImplementedError

    def list_list_members(self, list_name: str) -> list[dict]:
        """Return members of a creator list."""
        raise NotImplementedError

    def profile_growth(self, days: int = 14) -> list[dict]:
        """Daily distinct-first-seen profile counts, oldest first.

        Each item is {date: 'YYYY-MM-DD', count: int}. Drives the dashboard's
        Creator Growth series; empty store returns []."""
        raise NotImplementedError

    def list_views(self) -> list[dict]:
        """Read-model views over the profile/metadata stores.

        Each item is {name, columns: [], rows: int, sample: [dict]}. Powers the
        /api/database/views inspector without exposing raw table DDL."""
        raise NotImplementedError

    def list_tables(self) -> list[dict]:
        """App tables + column metadata for the /database inspector."""
        raise NotImplementedError

    def ingest_from_keylist(self, keylist_path: str, on_event=None, table: str | None = None) -> dict:
        raise NotImplementedError