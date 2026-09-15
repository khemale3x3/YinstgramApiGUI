from __future__ import annotations
import re
from dataclasses import asdict

from app.core.config import settings
from app.core.domain.pipeline import ScraperConfig


class SettingsService:
    """Use case: read and update application settings from the admin UI.

    Values are surfaced from the pydantic `settings` singleton. Updates are
    validated against a whitelist of mutable keys and written back to the
    backend `.env` file so they survive a restart.
    """

    MUTABLE = frozenset(
        {
            "debug",
            "cors_origins",
            "admin_email",
            "admin_password",
            "jwt_secret",
            "jwt_expires_minutes",
            "scraper_max_workers",
            "scraper_max_posts",
            "scraper_headless",
            "scraper_active_sessions",
            "scraper_timeout",
            "scraper_test_mode",
            "scraper_max_test_profiles",
            "pg_enabled",
            "pg_host",
            "pg_port",
            "pg_user",
            "pg_password",
            "pg_name",
            "pg_schema",
            "db_server",
            "db_name",
            "db_user",
            "db_password",
            "db_table",
            "db_driver",
            "s3_bucket",
            "s3_region",
            "s3_access_key",
            "s3_secret_key",
            "storage_provider",
            "storage_local_dir",
            "gcs_bucket",
            "gcs_project",
            "drive_folder_id",
            "instagram_graph_api_version",
            "instagram_graph_business_account_id",
            "instagram_graph_access_token",
            "export_formats",
    }
    )

    SECRET_KEYS = frozenset(
        {"admin_password", "jwt_secret", "db_password", "s3_secret_key", "s3_access_key", "pg_password", "instagram_graph_access_token"}
    )

    def to_dict(self, include_secrets: bool = False) -> dict:
        data = {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "admin_email": settings.admin_email,
            "data_dir": settings.data_dir,
            "session_dir": settings.session_dir,
            "pipeline_dir": settings.pipeline_dir,
            "cors_origins": list(settings.cors_origins),
            "scraper": {
                "max_workers": settings.scraper_max_workers,
                "max_posts": settings.scraper_max_posts,
                "headless": settings.scraper_headless,
                "active_sessions": settings.scraper_active_sessions,
                "timeout": settings.scraper_timeout,
                "test_mode": settings.scraper_test_mode,
                "max_test_profiles": settings.scraper_max_test_profiles,
                "delay_range": list(settings.delay_range),
            },
            "postgres": {
                "enabled": bool(settings.pg_enabled),
                "host": settings.pg_host,
                "port": settings.pg_port,
                "user": settings.pg_user,
                "name": settings.pg_name,
                "schema": settings.pg_schema,
                "configured": bool(settings.pg_host and settings.pg_user and settings.pg_password),
            },
            "database": {
                "server": settings.db_server,
                "name": settings.db_name,
                "user": settings.db_user,
                "table": settings.db_table,
                "driver": settings.db_driver,
                "configured": bool(settings.db_server and settings.db_password),
            },
            "storage": {
                "provider": settings.storage_provider,
                "local_dir": settings.storage_local_dir,
                "bucket": settings.s3_bucket,
                "region": settings.s3_region,
                "gcs_bucket": settings.gcs_bucket,
                "gcs_project": settings.gcs_project,
                "drive_folder_id": settings.drive_folder_id,
                "configured": bool(settings.s3_access_key and settings.s3_secret_key),
            },
            "instagram_graph": {
                "api_version": settings.instagram_graph_api_version,
                "business_account_id": settings.instagram_graph_business_account_id,
                "configured": bool(settings.instagram_graph_business_account_id and settings.instagram_graph_access_token),
            },
            "export_formats": list(settings.export_formats),
            "jwt_expires_minutes": settings.jwt_expires_minutes,
        }
        if include_secrets:
            data["_secrets"] = {k: getattr(settings, k, "") for k in self.SECRET_KEYS}
        return data

    def update(self, patch: dict) -> dict:
        unknown = [k for k in patch if k not in self.MUTABLE]
        if unknown:
            raise ValueError(f"unknown setting(s): {', '.join(unknown)}")
        for key, value in patch.items():
            if key == "cors_origins" or key == "export_formats":
                setattr(settings, key, _coerce_list(value))
            else:
                current = getattr(settings, key, None)
                if isinstance(current, bool):
                    value = _coerce_bool(value)
                elif isinstance(current, int):
                    value = int(value)
                setattr(settings, key, value)
        self._persist_env(patch)
        return self.to_dict(include_secrets=False)

    def scraper_config(self) -> ScraperConfig:
        return ScraperConfig(
            max_workers=settings.scraper_max_workers,
            max_posts=settings.scraper_max_posts,
            headless=settings.scraper_headless,
            active_sessions=settings.scraper_active_sessions,
            timeout=settings.scraper_timeout,
            delay_range=list(settings.delay_range),
            test_mode=settings.scraper_test_mode,
            max_test_profiles=settings.scraper_max_test_profiles,
        )

    def _persist_env(self, patch: dict) -> None:
        from app.core.config import BACKEND_DIR

        dotenv = BACKEND_DIR / ".env"
        lines: list[str] = []
        if dotenv.exists():
            lines = dotenv.read_text("utf-8").splitlines()
        updated = {k: v for k, v in patch.items()}

        output: list[str] = []
        keys_written = set()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                output.append(line)
                continue
            key, _, _rest = stripped.partition("=")
            key = key.strip()
            if key in updated:
                output.append(f"{key}={_format_env(updated.pop(key))}")
                keys_written.add(key)
            else:
                output.append(line)
        for key, value in updated.items():
            if key not in keys_written:
                output.append(f"{key}={_format_env(value)}")
        dotenv.write_text("\n".join(output) + "\n", "utf-8")


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_list(value) -> list:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)


def _format_env(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)