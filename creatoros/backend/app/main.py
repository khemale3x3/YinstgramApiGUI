"""Composition root.

Wires the hexagonal layers together: creates the driven (secondary) adapters,
injects them into the use-cases, and exposes them through the driving (primary)
HTTP adapter. This is the only place allowed to know about all the pieces.

Phase 2 adds the admin plane: JWT auth, background jobs, projects, settings,
sessions, the metadata database and S3 storage — all backed by the user's
ported pipeline (pipeline/ directory is added to sys.path so the copied
scripts and their sibling imports resolve).

Phase 3 adds access control: RBAC store (users/features/menus/audit) in
creatoros.db, a dynamic sidebar contract via /api/auth/me, backend-enforced
feature gates on every router, and the dashboard control-center endpoints.
"""
from __future__ import annotations

import hmac
import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from app.adapters.primary.api.clientinfo import meta_from_request
from app.adapters.primary.api.deps import (
    build_require_admin,
    build_require_feature,
)
from app.adapters.primary.api.routes.accounts import build_router as build_accounts_router
from app.adapters.primary.api.routes.admin import build_router as build_admin_router
from app.adapters.primary.api.routes.auth import build_router as build_auth_router
from app.adapters.primary.api.routes.campaigns import build_router as build_campaigns_router
from app.adapters.primary.api.routes.creators import build_router as build_creators_router
from app.adapters.primary.api.routes.dashboard import build_router as build_dashboard_router
from app.adapters.primary.api.routes.database import build_router as build_database_router
from app.adapters.primary.api.routes.jobs import build_router as build_jobs_router
from app.adapters.primary.api.routes.instagram import build_router as build_instagram_router
from app.adapters.primary.api.routes.marketplace import build_router as build_marketplace_router
from app.adapters.primary.api.routes.projects import build_router as build_projects_router
from app.adapters.primary.api.routes.sessions import build_router as build_sessions_router
from app.adapters.primary.api.routes.settings import build_router as build_settings_router
from app.adapters.primary.api.routes.storage import build_router as build_storage_router
from app.adapters.primary.api.routes.tracking import build_router as build_tracking_router
from app.adapters.secondary.access.admin_store import SqliteAdminStore
from app.adapters.secondary.auth.jwt import JwtTokenAdapter
from app.adapters.secondary.database.scraper_store import ScraperSqliteAdapter
from app.adapters.secondary.database.sqlserver import SqlServerAdapter
from app.adapters.secondary.instagrapi.client import InstagrapiAdapter
from app.adapters.secondary.pipeline.analyzer import PipelineAnalyzerAdapter
from app.adapters.secondary.pipeline.exporters import PipelineExporterAdapter
from app.adapters.secondary.pipeline.scraper import SeleniumScraperAdapter
from app.adapters.secondary.pipeline.sessions import EnvSessionSource
from app.adapters.secondary.sessions.file_store import FileSessionStore, InstagrapiFactory
from app.adapters.secondary.storage.s3 import S3StorageAdapter
from app.adapters.secondary.store.sqlite import SqliteJobStore, SqliteProjectStore
from app.core.config import ROOT_DIR, settings
from app.core.services.account_service import AccountService
from app.core.services.admin_service import AdminService
from app.core.services.auth_service import AuthService, verify_password
from app.core.services.campaign_service import CampaignService
from app.core.services.dashboard_service import DashboardService
from app.core.services.database_service import DatabaseService
from app.core.services.instagram_service import InstagramService
from app.core.services.job_service import JobService
from app.core.services.marketplace_service import MarketplaceService
from app.core.services.pipeline_service import PipelineService
from app.core.services.project_service import ProjectService
from app.core.services.session_service import SessionService
from app.core.services.settings_service import SettingsService
from app.core.services.storage_service import StorageService

# Make the copied pipeline scripts importable by their absolute sibling names
# (analyze_insta_except imports `from bio_location import ...` etc.).
for path in (Path(settings.pipeline_dir), ROOT_DIR):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _admin_password_verifier():
    if settings.admin_password_hash:
        return lambda pwd: verify_password(pwd or "", settings.admin_password_hash)
    return lambda pwd: hmac.compare_digest(pwd or "", settings.admin_password)


app_state: dict = {"pg_active": False}


def _make_stores():
    """Build the driven stores, preferring the PostgreSQL app store.

    PG_* settings are read from backend/.env (see config.py). When Postgres is
    configured but unreachable the process logs a warning and falls back to the
    SQLite stores so the API never fails to boot on a fresh machine.
    """
    if settings.pg_enabled:
        try:
            from app.adapters.secondary.postgres.connection import init_schema
            from app.adapters.secondary.postgres.store import (
                PgAdminStore,
                PgCampaignStore,
                PgJobStore,
                PgProfileStore,
                PgProjectStore,
            )

            applied = init_schema()
            print(
                f"[creatoros] PostgreSQL primary store ready "
                f"({settings.pg_user}@{settings.pg_host}:{settings.pg_port}/{settings.pg_name}) "
                f"— applied: {', '.join(applied) or 'none'}"
            )
            app_state["pg_active"] = True
            return PgJobStore(), PgProjectStore(), PgProfileStore(), PgAdminStore()
        except Exception as exc:  # noqa: BLE001 - degrade to sqlite on first run
            print(f"[creatoros] PostgreSQL unavailable ({exc}); falling back to SQLite stores")
    admin_store = SqliteAdminStore()
    job_store = SqliteJobStore()
    project_store = SqliteProjectStore()
    scraper_store = ScraperSqliteAdapter()
    return job_store, project_store, scraper_store, admin_store


def _build_app() -> FastAPI:
    # ----------------------------------------------------------- admin plane
    job_store, project_store, scraper_store, admin_store = _make_stores()
    admin_service = AdminService(admin_store)

    token_adapter = JwtTokenAdapter(
        secret=settings.jwt_secret,
        expires_minutes=settings.jwt_expires_minutes,
    )
    auth_service = AuthService(
        tokens=token_adapter,
        admin=admin_store,
        email=settings.admin_email,
        password_verifier=_admin_password_verifier(),
    )
    require_admin = build_require_admin(auth_service)
    require_feature = build_require_feature(require_admin, admin_service)

    # ------------------------------------------------------- secondary adapters
    # Phase-1: instagrapi + account sessions
    session_store = FileSessionStore()
    instagram_factory = InstagrapiFactory()

    # Phase-2/3: stores live in PostgreSQL (Pg*) with a SQLite fallback, above;
    # the pipeline, ingest and S3 adapters are unchanged.
    sqlserver = SqlServerAdapter()
    s3 = S3StorageAdapter()
    cookie_sessions = EnvSessionSource()
    session_service = SessionService(cookie_sessions)

    instagram_service = InstagramService(instagram=InstagrapiAdapter())
    account_service = AccountService(
        sessions=session_store,
        instagram_factory=instagram_factory,
    )
    project_service = ProjectService(projects=project_store, data_dir=settings.data_dir)

    pipeline_service = PipelineService(
        scraper=SeleniumScraperAdapter(),
        analyzer=PipelineAnalyzerAdapter(),
        exporter=PipelineExporterAdapter(),
        sessions=cookie_sessions,
        projects=project_service,
        metadata_db=scraper_store,
        ingest_db=sqlserver,
        instagram_factory=instagram_factory,
        instagram_sessions=session_store,
    )

    if app_state["pg_active"]:
        from app.adapters.secondary.postgres.store import PgCampaignStore

        campaign_store = PgCampaignStore()
    else:
        from app.adapters.secondary.store.campaign_store import SqliteCampaignStore

        campaign_store = SqliteCampaignStore()
    campaign_service = CampaignService(
        store=campaign_store,
        db=DatabaseService(local=scraper_store, remote=sqlserver),
    )

    dashboard_service = DashboardService(
        jobs=job_store,
        profiles=scraper_store,
        sessions=session_service,
        storage=s3,
        admin=admin_store,
        campaigns=campaign_store,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Instagram Creator Intelligence Platform",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def record_api_traffic(request, call_next):
        """Log every API call into api_traffic (user, path, status, latency, client).

        Best-effort: any tracking failure is swallowed so it can never break a
        request. Connections (signup/login) are recorded separately by the auth
        router for cleaner, lower-cardinality rows.
        """
        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)
        if request.method in ("OPTIONS", "HEAD"):
            return await call_next(request)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start) * 1000)
            email = ""
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                try:
                    claims = token_adapter.verify_token(auth[7:])
                    email = claims.get("sub", "") or ""
                except Exception:
                    email = ""
            meta = meta_from_request(request)
            admin_service.record_traffic(
                user=email or "anonymous",
                email=email,
                meta={
                    **meta,
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception:
            raise

    # ------------------------------------------------------ primary adapters
    app.include_router(
        build_creators_router(
            instagram_service, require_admin, dependencies=[Depends(require_feature("creators"))]
        )
    )
    app.include_router(
        build_accounts_router(
            account_service, require_admin, dependencies=[Depends(require_feature("accounts"))]
        )
    )
    app.include_router(build_auth_router(auth_service, admin_service))
    app.include_router(build_instagram_router(instagram_factory, session_store, scraper_store, require_admin, dependencies=[Depends(require_feature("publishing"))]))
    app.include_router(
        build_jobs_router(
            JobService(job_store),
            pipeline_service,
            DatabaseService(local=scraper_store, remote=sqlserver),
            StorageService(s3),
            project_service,
            require_admin,
            dependencies=[Depends(require_feature("jobs"))],
        )
    )
    app.include_router(
        build_projects_router(
            project_service, require_admin, dependencies=[Depends(require_feature("projects"))]
        )
    )
    app.include_router(
        build_settings_router(
            SettingsService(), require_admin, dependencies=[Depends(require_feature("settings"))]
        )
    )
    app.include_router(
        build_sessions_router(
            session_service, require_admin, dependencies=[Depends(require_feature("sessions"))]
        )
    )
    app.include_router(
        build_database_router(
            DatabaseService(local=scraper_store, remote=sqlserver),
            require_admin,
            dependencies=[Depends(require_feature("database"))],
        )
    )
    app.include_router(
        build_storage_router(
            StorageService(s3), require_admin, dependencies=[Depends(require_feature("storage"))]
        )
    )
    app.include_router(
        build_dashboard_router(dashboard_service, require_admin, require_feature)
    )
    app.include_router(build_admin_router(admin_service, require_admin, require_feature))
    app.include_router(build_tracking_router(admin_service, require_admin, require_feature))
    app.include_router(build_campaigns_router(campaign_service, require_feature))
    app.include_router(
        build_marketplace_router(
            MarketplaceService(
                db=DatabaseService(local=scraper_store, remote=sqlserver),
                instagram=instagram_service,
            ),
            require_feature,
        )
    )

    @app.get("/")
    def root() -> dict:
        return {
            "application": settings.app_name,
            "version": settings.app_version,
            "status": "running",
        }

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "healthy",
            "version": settings.app_version,
        }

    return app


app = _build_app()