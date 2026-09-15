"""S3 adapter — object storage on bucket veel-data-processing via boto3."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.ports.storage import StoragePort


class S3StorageAdapter(StoragePort):
    """Driven adapter: S3 upload/download/list via boto3."""

    def __init__(self, bucket=None, region=None, access_key=None, secret_key=None):
        self._bucket = bucket or settings.s3_bucket
        self._region = region if region is not None else (settings.s3_region or None)
        self._access_key = access_key if access_key is not None else (settings.s3_access_key or "")
        self._secret_key = secret_key if secret_key is not None else (settings.s3_secret_key or "")

    def _client(self):
        import boto3
        from botocore.config import Config

        if not (self._access_key and self._secret_key):
            raise ValueError(
                "S3 not configured (s3_access_key / s3_secret_key)"
            )
        kwargs = dict(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(
                connect_timeout=10,
                read_timeout=15,
                retries={"max_attempts": 1},
            ),
        )
        if self._region:
            kwargs["region_name"] = self._region
        session = boto3.Session(**kwargs)
        return session.client("s3")

    def available(self) -> bool:
        if not (self._access_key and self._secret_key):
            return False
        try:
            self._client().head_bucket(Bucket=self._bucket)
            return True
        except Exception:
            return False

    def upload_file(self, local_path, key) -> str:
        self._client().upload_file(str(local_path), self._bucket, str(key))
        return str(key)

    def download_file(self, key, local_path) -> str:
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client().download_file(self._bucket, str(key), str(local_path))
        return str(local_path)

    def list_keys(self, prefix="") -> list[str]:
        paginator = self._client().get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def upload_directory(self, local_dir, prefix="", on_event=None) -> dict:
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"directory not found: {local_dir}")

        client = self._client()
        uploaded = 0
        total_bytes = 0
        files = [p for p in local_dir.rglob("*") if p.is_file()]
        for i, path in enumerate(files, start=1):
            rel = path.relative_to(local_dir).as_posix()
            key = f"{prefix.rstrip('/')}/{rel}" if prefix else rel
            client.upload_file(str(path), self._bucket, key)
            uploaded += 1
            total_bytes += path.stat().st_size
            if on_event and i % 25 == 0:
                on_event("log", f"uploading... {i}/{len(files)} ({key})")
        return {"files": uploaded, "bytes": total_bytes, "prefix": prefix}