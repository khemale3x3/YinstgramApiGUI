from __future__ import annotations
from abc import ABC, abstractmethod

from app.core.domain.creator import Creator
from app.core.domain.post import CreatorPost


class InstagramPort(ABC):
    """Secondary port for any Instagram engine.

    The whole application talks to Instagram through this interface. The
    instagrapi adapter is one implementation; a future official API or mock
    can implement it without touching the rest of the system.
    """

    @property
    @abstractmethod
    def username(self) -> str | None:
        """Username of the authenticated account, if any."""

    @abstractmethod
    def get_profile(self, username: str) -> Creator:
        """Fetch a creator profile by username."""

    @abstractmethod
    def get_posts(self, username: str, amount: int = 10) -> list[CreatorPost]:
        """Fetch recent posts for an Instagram username."""

    @abstractmethod
    def search_users(self, query: str, count: int = 20) -> list[dict]:
        """Search accounts by keyword; returns lightweight profile dicts."""

    @abstractmethod
    def get_network(self, username: str, direction: str, amount: int = 100) -> list[dict]:
        """Fetch follower or following usernames for an Instagram account."""

    @abstractmethod
    def execute_action(self, action: str, payload: dict) -> dict:
        """Execute an authenticated publishing, community, or discovery action."""

    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """Authenticate and keep the session in memory."""

    @abstractmethod
    def load_session(self, settings: dict | None) -> None:
        """Restore a previously saved session state."""

    @abstractmethod
    def dump_session(self) -> dict:
        """Serialize the current session state for persistence."""

    @abstractmethod
    def verify_session(self) -> bool:
        """Check whether the loaded session is still accepted by Instagram."""