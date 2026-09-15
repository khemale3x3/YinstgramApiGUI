from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class StoragePort(ABC):
    """Secondary port for object storage (S3 bucket veel-data-processing)."""

    @abstractmethod
    def available(self) -> bool:
        """Whether credentials/bucket are configured."""

    @abstractmethod
    def upload_file(self, local_path: str | Path, key: str) -> str:
        """Upload a single file. Returns the key."""

    @abstractmethod
    def download_file(self, key: str, local_path: str | Path) -> str:
        """Download a single object. Returns the local path."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """List object keys under an optional prefix."""

    @abstractmethod
    def upload_directory(self, local_dir: str | Path, prefix: str = "", on_event=None) -> dict:
        """Upload every file under local_dir, preserving relative paths."""