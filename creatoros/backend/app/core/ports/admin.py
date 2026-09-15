"""Secondary port for RBAC + feature-flag + audit + tracking persistence."""
from __future__ import annotations
from abc import ABC, abstractmethod


class AdminStorePort(ABC):
    """Persist users, feature flags, menu items, audit and connection/traffic logs."""

    @abstractmethod
    def get_user_by_email(self, email: str):
        """Return a User by (lowercased) email, or None."""

    @abstractmethod
    def get_user_by_id(self, user_id: str):
        """Return a User by id, or None."""

    @abstractmethod
    def update_user(self, user_id: str, role: str | None = None, status: str | None = None,
                    name: str | None = None, username: str | None = None):
        """Patch role / status / name / username on a user row."""

    @abstractmethod
    def upsert_user(self, user) -> "User":
        """Create or update a user (keyed on email)."""

    @abstractmethod
    def record_login(self, email: str) -> None:
        """Stamp last_login on a user (no-op if unknown)."""

    @abstractmethod
    def list(self) -> list:
        """Return all users, newest first."""

    @abstractmethod
    def list_features(self) -> list:
        """Return all FeatureFlag entities."""

    @abstractmethod
    def get_feature(self, key: str):
        """Return a FeatureFlag by key, or None."""

    @abstractmethod
    def set_feature(self, key: str, enabled: bool):
        """Flip a feature flag globally. Unknown keys are created."""

    @abstractmethod
    def list_menus(self) -> list:
        """Return all MenuItem entities."""

    @abstractmethod
    def audit(self, user: str, action: str, target: str = "", detail: str = "") -> None:
        """Append an audit log entry."""

    @abstractmethod
    def list_audit(self, limit: int = 50) -> list:
        """Return the most recent audit entries."""

    # ------------------------------------------------------------------ tracking
    @abstractmethod
    def record_connection(self, user: str, event: str, ip: str = "", user_agent: str = "",
                          device: str = "", browser: str = "", os: str = "", location: str = "") -> None:
        """Log a signup/login connection event (IP, location, device, UA)."""

    @abstractmethod
    def record_traffic(self, user: str, email: str, method: str, path: str, status: int,
                       duration_ms: int, ip: str = "", user_agent: str = "", device: str = "",
                       browser: str = "", os: str = "") -> None:
        """Log one API request (who called what endpoint, with what result)."""

    @abstractmethod
    def list_traffic(self, limit: int = 200) -> list:
        """Return recent API traffic, newest first."""

    @abstractmethod
    def list_connections(self, limit: int = 100) -> list:
        """Return recent connection events (signups/logins), newest first."""

    @abstractmethod
    def traffic_stats(self) -> dict:
        """Aggregate totals: requests, avg/max duration, status counts, top users."""