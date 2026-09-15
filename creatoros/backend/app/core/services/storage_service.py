from __future__ import annotations
from pathlib import Path

from app.core.ports.storage import StoragePort


class StorageService:
    """Use case: expose object-storage operations to the admin UI."""

    def __init__(self, storage: StoragePort | None):
        self._storage = storage

    def available(self) -> bool:
        return self._storage is not None and self._storage.available()

    def status(self) -> dict:
        if self._storage is None:
            return {"available": False}
        return {"available": self._storage.available(), "type": type(self._storage).__name__}

    def list_keys(self, prefix: str = "") -> list[str]:
        if self._storage is None:
            raise ValueError("S3 not configured")
        return self._storage.list_keys(prefix)

    def upload_file(self, local_path: str | Path, key: str) -> str:
        if self._storage is None:
            raise ValueError("S3 not configured")
        return self._storage.upload_file(local_path, key)

    def download_file(self, key: str, local_path: str | Path) -> str:
        if self._storage is None:
            raise ValueError("S3 not configured")
        return self._storage.download_file(key, local_path)

    def upload_directory(self, local_dir: str | Path, prefix: str = "", on_event=None) -> dict:
        if self._storage is None:
            raise ValueError("S3 not configured")
        return self._storage.upload_directory(local_dir, prefix=prefix, on_event=on_event)