from __future__ import annotations
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for adding an Instagram account."""

    username: str = Field(min_length=1, description="Instagram username")
    password: str = Field(min_length=1, description="Instagram password (used once)")


class AccountListResponse(BaseModel):
    accounts: list[str]


class VerifyResponse(BaseModel):
    verified: bool
    message: str = ""


# ---------------------------------------------------------------- admin/auth
class AdminLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    email: str
    role: str


class SignupRequest(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(default="", max_length=120)
    password: str = Field(min_length=8, max_length=256)


class MeResponse(BaseModel):
    email: str
    role: str
    name: str = ""
    username: str = ""
    status: str = "active"
    created_at: str = ""
    last_login: str = ""
    last_activity: str = ""
    users_managed: int = 0
    permissions: list[dict] = []
    instagram_accounts: list[dict] = []
    assigned_projects: list[dict] = []
    features: list[dict] = []
    menus: dict[str, list[dict]] = {}


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=256)


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|user)$")
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=100)


class FeatureUpdateRequest(BaseModel):
    enabled: bool


# ------------------------------------------------------------------- projects
class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1)


class UrlListRequest(BaseModel):
    urls: list[str] = Field(min_length=1)


class UrlRemoveRequest(BaseModel):
    urls: list[str] = Field(min_length=1)


# ----------------------------------------------------------------------- jobs
class JobCreateRequest(BaseModel):
    kind: str = Field(pattern="^(scrape|network_scrape|analyze|export|full|ingest|s3_upload|s3_download|index)$")
    project: str | None = None
    with_gender: bool = True
    with_csv: bool = True
    with_jpg: bool = True
    test_limit: int | None = None
    urls: list[str] | None = None
    username: str | None = None
    usernames: list[str] | None = None
    direction: str | None = Field(default=None, pattern="^(followers|following)$")
    source: str | None = None     # keylist path for ingest / local dir for upload
    table: str | None = None
    destination: str | None = None
    s3_prefix: str | None = None
    s3_key: str | None = None


# ------------------------------------------------------------------- settings
class SettingsUpdateRequest(BaseModel):
    debug: bool | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    jwt_secret: str | None = None
    jwt_expires_minutes: int | None = None
    cors_origins: list[str] | None = None
    export_formats: list[str] | None = None
    scraper_max_workers: int | None = None
    scraper_max_posts: int | None = None
    scraper_headless: bool | None = None
    scraper_active_sessions: int | None = None
    scraper_timeout: int | None = None
    scraper_test_mode: bool | None = None
    scraper_max_test_profiles: int | None = None
    pg_enabled: bool | None = None
    pg_host: str | None = None
    pg_port: int | None = None
    pg_user: str | None = None
    pg_password: str | None = None
    pg_name: str | None = None
    pg_schema: str | None = None
    db_server: str | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_table: str | None = None
    db_driver: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    storage_provider: str | None = Field(default=None, pattern="^(local|s3|gcs|drive)$")
    storage_local_dir: str | None = None
    gcs_bucket: str | None = None
    gcs_project: str | None = None
    drive_folder_id: str | None = None
    instagram_graph_api_version: str | None = None
    instagram_graph_business_account_id: str | None = None
    instagram_graph_access_token: str | None = None


# ---------------------------------------------------------------------- ingest
class IngestRequest(BaseModel):
    keylist: str | None = None          # absolute path
    table: str | None = None


class StorageTransferRequest(BaseModel):
    local: str | None = None
    key: str | None = None
    prefix: str | None = None
    destination: str | None = None