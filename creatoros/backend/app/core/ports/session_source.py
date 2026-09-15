from __future__ import annotations
from abc import ABC, abstractmethod


class SessionSourcePort(ABC):
    """Secondary port for Instagram session material.

    CreatorOS inherits two workflows from the user's pipeline:

    - cookie sessions: `sessionid` cookie values declared as
      INSTA_SESSION_1..N in a .env file (Selenium scraper uses these).
    - instagrapi sessions: JSON session files under `sessions/<username>.json`.

    This port abstracts both so the Selenium scraper, the session monitor,
    and the admin UI can share one source of truth.
    """

    @abstractmethod
    def list_sessions(self) -> list[dict]:
        """Return one dict per available session:

        {key, label, kind: "cookie"|"instagrapi", username_or_index, active,
         preview, valid: bool|None, error: str|None}
        """

    @abstractmethod
    def active_sessions(self) -> list[str]:
        """Cookie session ids designated as the active (first-N) set."""

    @abstractmethod
    def backup_sessions(self) -> list[str]:
        """Cookie session ids beyond the active set (fallback pool)."""

    @abstractmethod
    def all_cookie_sessions(self) -> list[str]:
        """Every cookie session id, in declared order."""

    @abstractmethod
    def import_from_env(self, env_path: str | None = None) -> int:
        """Read INSTA_SESSION_* entries from an env file. Returns count read."""
        raise NotImplementedError