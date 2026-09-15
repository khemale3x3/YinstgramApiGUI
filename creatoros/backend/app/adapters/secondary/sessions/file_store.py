import json
import os
import tempfile
from pathlib import Path

from app.adapters.secondary.instagrapi.client import InstagrapiAdapter
from app.core.config import settings
from app.core.ports.session_store import SessionStorePort

SESSION_EXT = ".json"


class InstagrapiFactory:
    """Builds `InstagrapiAdapter` instances, optionally pre-loaded with a session.

    Kept next to the adapter so the composition root can hand a factory to the
    account use case without importing instagrapi-specific types.
    """

    def __call__(self, session: dict | None = None) -> InstagrapiAdapter:
        client = InstagrapiAdapter()
        if session:
            client.load_session(session)
        return client


class FileSessionStore(SessionStorePort):
    """Driven adapter that persists instagrapi sessions as JSON files.

    One file per account under the configured session directory. Files are
    gitignored and should be treated as secrets — they hold session auth state.
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self._root = Path(root_dir or settings.session_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, username: str) -> Path:
        return self._root / f"{username}{SESSION_EXT}"

    def list_accounts(self) -> list[str]:
        return sorted(p.stem for p in self._root.glob(f"*{SESSION_EXT}"))

    def has(self, username: str) -> bool:
        return self._path(username).exists()

    def load(self, username: str) -> dict | None:
        path = self._path(username)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, username: str, settings: dict) -> None:
        path = self._path(username)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self._root, suffix=SESSION_EXT)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(settings, handle, indent=2)
            os.replace(tmp_name, path)
        except BaseException:
            os.unlink(tmp_name)
            raise

    def remove(self, username: str) -> bool:
        path = self._path(username)
        if path.exists():
            path.unlink()
            return True
        return False