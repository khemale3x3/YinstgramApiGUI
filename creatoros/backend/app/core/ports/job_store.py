from __future__ import annotations
from abc import ABC, abstractmethod


class JobStorePort(ABC):
    """Secondary port for persisting background jobs."""

    @abstractmethod
    def create(self, job) -> "job":
        """Persist a new job and return it."""

    @abstractmethod
    def update(self, job) -> "job":
        """Persist a changed job and return it."""

    @abstractmethod
    def get(self, job_id: str):
        """Return a job by id, or None."""

    @abstractmethod
    def list(self, limit: int = 50) -> list:
        """Return most recent jobs first."""

    @abstractmethod
    def count_by_status(self) -> dict:
        """Return {status: count} across all jobs."""

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Delete a job. Returns True if it existed."""