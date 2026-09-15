"""Sessions adapter — reads INSTA_SESSION_N / INSTA_ACCOUNT_N env entries.

Mirrors the user's traits: sessions declared as INSTA_SESSION_1..N become the
load-balanced cookie pool; the first `active_sessions` entries are the active
set, the remainder act as backups the scraper falls back to when a session is
refused.
"""
from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

from app.core.config import settings
from app.core.ports.session_source import SessionSourcePort

_SESSION_ENV_RE = re.compile(r"^INSTA_SESSION_(\d+)", re.IGNORECASE)
_ACCOUNT_ENV_RE = re.compile(r"^INSTA_ACCOUNT_(\d+)", re.IGNORECASE)


def _parse_env_file(path: str | Path | None) -> dict:
    env: dict = {}
    if not path:
        return env
    path = Path(path)
    if not path.exists():
        return env
    for line in path.read_text("utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


class EnvSessionSource(SessionSourcePort):
    """Driven adapter: cookie sessions from backend/.env."""

    def __init__(self, env_path: str | Path | None = None):
        from app.core.config import BACKEND_DIR

        self._env_path = Path(env_path) if env_path else BACKEND_DIR / ".env"

    def _read(self) -> dict:
        return _parse_env_file(self._env_path)

    def all_cookie_sessions(self) -> list[str]:
        env = self._read()
        entries = [(int(m.group(1)), val) for key, val in env.items() if (m := _SESSION_ENV_RE.match(key))]
        entries.sort(key=lambda item: item[0])
        return [val for _, val in entries]

    def active_sessions(self) -> list[str]:
        ids = self.all_cookie_sessions()
        limit = max(1, settings.scraper_active_sessions) if ids else 0
        return ids[:limit]

    def backup_sessions(self) -> list[str]:
        ids = self.all_cookie_sessions()
        limit = max(1, settings.scraper_active_sessions) if ids else 0
        return ids[limit:]

    def list_sessions(self) -> list[dict]:
        env = self._read()
        records: list[dict] = []
        max_index = max(
            [int(m.group(1)) for key in env if (m := _SESSION_ENV_RE.match(key))] or [0]
        )
        active_set = set(self.active_sessions())

        for key, value in env.items():
            session_match = _SESSION_ENV_RE.match(key)
            account_match = _ACCOUNT_ENV_RE.match(key)
            if session_match:
                index = int(session_match.group(1))
                records.append(
                    {
                        "key": key,
                        "label": f"session #{index}",
                        "kind": "cookie",
                        "index": index,
                        "active": value in active_set,
                        "preview": _preview(value),
                        "status": "configured",
                    }
                )
            elif account_match:
                username, _, _pw = value.partition(":")
                records.append(
                    {
                        "key": key,
                        "label": f"account #{account_match.group(1)}: {username or '?'}",
                        "kind": "account",
                        "index": int(account_match.group(1)),
                        "active": False,
                        "preview": username or "?",
                        "status": "credentials (not logged in yet)" if ":" in value else "misconfigured",
                    }
                )

        instagrapi_names = _list_instagrapi_sessions()
        for name in instagrapi_names:
            records.append(
                {
                    "key": f"instagrapi:{name}",
                    "label": f"instagrapi session: {name}",
                    "kind": "instagrapi",
                    "username": name,
                    "active": False,
                    "preview": name,
                    "status": "saved JSON session",
                }
            )
        records.sort(key=lambda r: (r.get("kind"), r.get("index") if r.get("index") is not None else 0))
        return records

    def import_from_env(self, env_path: str | Path | None = None) -> int:
        source = _parse_env_file(env_path) if env_path else _parse_env_file(self._env_path)
        relevant = {
            key: val
            for key, val in source.items()
            if _SESSION_ENV_RE.match(key) or _ACCOUNT_ENV_RE.match(key)
        }
        if not relevant:
            return 0

        self._env_path.parent.mkdir(parents=True, exist_ok=True)
        existing = _parse_env_file(self._env_path)
        lines = self._env_path.read_text("utf-8") if self._env_path.exists() else ""
        kept_lines = []
        for line in lines.splitlines():
            stripped = line.strip()
            key = stripped.partition("=")[0].strip()
            if _SESSION_ENV_RE.match(key) or _ACCOUNT_ENV_RE.match(key):
                continue  # will be re-added below
            kept_lines.append(line)

        merged = dict(existing)
        merged.update(relevant)
        output = kept_lines + [f"{key}={val}" for key, val in merged.items() if _SESSION_ENV_RE.match(key) or _ACCOUNT_ENV_RE.match(key)]
        self._env_path.write_text("\n".join(output) + "\n", "utf-8")
        return len(relevant)


def _preview(value: str) -> str:
    return f"...{value[-10:]}" if len(value) > 10 else value


def _list_instagrapi_sessions() -> list[str]:
    session_dir = Path(settings.session_dir)
    if not session_dir.exists():
        return []
    names = []
    for path in sorted(session_dir.glob("*.json")):
        if (session_dir / path.name).stat().st_size > 0:
            names.append(path.stem)
    return names