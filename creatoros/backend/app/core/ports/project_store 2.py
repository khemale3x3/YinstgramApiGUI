from __future__ import annotations
from abc import ABC, abstractmethod


class ProjectStorePort(ABC):
    """Secondary port for persisting projects and their URL lists.

    The pending/done URL pair mirrors the user's input.csv / inputdone.csv
    workflow — a URL leaves the pending list the moment it is scraped and is
    recorded as done.
    """

    @abstractmethod
    def create(self, project) -> "project":
        """Register a new project."""

    @abstractmethod
    def get(self, name: str):
        """Return a project by name, or None."""

    @abstractmethod
    def update(self, project) -> "project":
        """Persist project-level counters/status."""

    @abstractmethod
    def list(self) -> list:
        """Return all projects."""

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a project and its URL rows."""

    # ------------------------------------------------------------ URL lists
    @abstractmethod
    def pending_urls(self, name: str) -> list[str]:
        """URLs still to be scraped for a project."""

    @abstractmethod
    def done_urls(self, name: str) -> list[str]:
        """URLs already scraped for a project."""

    @abstractmethod
    def add_urls(self, name: str, urls: list[str], done: bool = False) -> int:
        """Add URLs to a project. Returns the number added."""

    @abstractmethod
    def remove_pending(self, name: str, urls: list[str]) -> int:
        """Remove URLs from the pending list."""

    @abstractmethod
    def mark_done(self, name: str, url: str) -> bool:
        """Move a URL from pending to done."""