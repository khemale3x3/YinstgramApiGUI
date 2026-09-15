from __future__ import annotations
from app.core.ports.session_source import SessionSourcePort


class SessionService:
    """Use case: expose Instagram session sources to the admin UI."""

    def __init__(self, source: SessionSourcePort):
        self._source = source

    def list(self) -> list[dict]:
        return self._source.list_sessions()

    def counts(self) -> dict:
        sessions = self._source.list_sessions()
        cookies = [s for s in sessions if s.get("kind") == "cookie"]
        instagrapi = [s for s in sessions if s.get("kind") == "instagrapi"]
        return {
            "cookie_total": len(cookies),
            "cookie_active": sum(1 for s in cookies if s.get("active")),
            "cookie_backup": sum(1 for s in cookies if not s.get("active")),
            "instagrapi": len(instagrapi),
            "total": len(sessions),
        }

    def import_from_env(self, env_path: str | None = None) -> int:
        return self._source.import_from_env(env_path)