"""PostgreSQL connection + schema bootstrap for the CreatorOS app store.

DDL lives in creatoros/data/postgres/*.sql (schema, views, procedures,
functions) and is applied idempotently every time the application boots, so a
fresh machine with the right PG_* settings is fully provisioned automatically.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras

from app.core.config import settings

log = logging.getLogger("creatoros.postgres")

SELECTED = False


def pg_dsn() -> str:
    return (
        f"host={settings.pg_host} port={settings.pg_port} "
        f"dbname={settings.pg_name} user={settings.pg_user} "
        f"password={settings.pg_password}"
    )


def is_enabled() -> bool:
    return bool(settings.pg_enabled and settings.pg_host and settings.pg_name)


@contextmanager
def pg_connect():
    """Yield a psycopg2 connection; commits on success, always closes."""
    conn = psycopg2.connect(pg_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def pg_cursor():
    """Yield a RealDictCursor bound to a fresh connection."""
    with pg_connect() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur


def schema_dir() -> Path:
    return Path(settings.data_dir) / "postgres"


def init_schema() -> list[str]:
    """Apply data/postgres/*.sql to the configured database.

    Files run in dependency order (schema → functions → procedures → views).
    Returns the list of files applied so callers can log the outcome.
    """
    global SELECTED
    applied: list[str] = []
    ordered = ["schema.sql", "functions.sql", "procedures.sql", "views.sql"]
    directory = schema_dir()
    if not directory.is_dir():
        raise FileNotFoundError(
            f"postgres schema directory not found: {directory} (check PG settings / data_dir)"
        )
    with pg_connect() as conn:
        for name in ordered:
            path = directory / name
            if not path.exists():
                continue
            sql = path.read_text("utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            applied.append(name)
    SELECTED = True
    return applied


def check_connection() -> dict:
    """Lightweight availability probe used by /api/database/status."""
    try:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user, version();")
                row = cur.fetchone()
        return {
            "available": True,
            "type": "postgres",
            "database": row[0],
            "user": row[1],
            "version": (row[2] or "").split(",")[0],
            "schema": settings.pg_schema,
        }
    except Exception as exc:  # pragma: no cover - depends on environment
        return {"available": False, "type": "postgres", "scheme": settings.pg_name, "error": str(exc)}