from __future__ import annotations
from abc import ABC, abstractmethod


class SessionStorePort(ABC):
    """Secondary port for persisting Instagram session state."""

    @abstractmethod
    def list_accounts(self) -> list[str]:
        """Usernames that currently hold a stored session."""

    @abstractmethod
    def has(self, username: str) -> bool:
        """Whether a session is stored for the given account."""

    @abstractmethod
    def load(self, username: str) -> dict | None:
        """Return the stored session settings, or None."""

    @abstractmethod
    def save(self, username: str, settings: dict) -> None:
        """Persist the session settings for an account."""

    @abstractmethod
    def remove(self, username: str) -> bool:
        """Delete a stored session. Returns True if it existed."""