from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# creatoros/backend/app/core/config.py
# -> creatoros/backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
# -> creatoros/backend/app
APP_DIR = Path(__file__).resolve().parent.parent
# -> creatoros
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "KreatOS API"
    app_version: str = "0.2.0"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    session_dir: str = str(ROOT_DIR / "sessions")
    data_dir: str = str(ROOT_DIR / "data")
    pipeline_dir: str = str(ROOT_DIR / "pipeline")

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    request_timeout: int = 15
    delay_range: list[float] = [1.0, 3.0]

    # ------------------------------------------------------------------ admin
    admin_email: str = "khemale05@gmail.com"
    admin_password: str = "Khem101$"
    admin_password_hash: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_expires_minutes: int = 720

    # -------------------------------------------------------------- pipeline
    scraper_max_workers: int = 8
    scraper_max_posts: int = 40
    scraper_headless: bool = True
    scraper_active_sessions: int = 5
    scraper_timeout: int = 30
    scraper_test_mode: bool = False
    scraper_max_test_profiles: int = 5

    # -------------------------------------------------------------- database
    metadata_db_path: str = str(ROOT_DIR / "data" / "creatoros.db")
    scraper_db_path: str = str(ROOT_DIR / "data" / "scraper_data.db")

    # -------------------------------------------------- postgres (app store)
    # CreatorOS persists its runtime data (jobs, projects, users, features,
    # menus, audit trail, scraped profiles) in a local PostgreSQL database.
    # DDL lives in data/postgres/*.sql and is applied automatically on boot.
    pg_enabled: bool = True
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "khem"
    pg_password: str = "Khem101$"
    pg_name: str = "yinstagram"
    pg_schema: str = "creatoros"

    db_server: str = ""
    db_name: str = "CreatorsDatabase"
    db_user: str = "sa"
    db_password: str = ""
    db_table: str = "dbo.prodmauploadvakodata"
    db_driver: str = "ODBC Driver 17 for SQL Server"

    # -------------------------------------------------------------------- s3
    s3_bucket: str = "veel-data-processing"
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Scraped artifact destination. Local and S3 are supported by the current
    # pipeline; cloud provider fields are retained for adapter configuration.
    storage_provider: str = "local"
    storage_local_dir: str = str(ROOT_DIR / "data" / "scraped")
    gcs_bucket: str = ""
    gcs_project: str = ""
    drive_folder_id: str = ""

    # ------------------------------------------------------------ exporter
    export_formats: list[str] = ["json", "jsonl", "csv"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()