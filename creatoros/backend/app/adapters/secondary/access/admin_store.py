"""SQLite adapter for RBAC, feature flags, menus and audit logs.

Lives in the same metadata database as jobs/projects (creatoros.db) so the
runtime stays a single-file store. Tables are seeded on first boot from
app.core.domain.access (FEATURES / MENU_ITEMS) — later admin-created rows are
preserved by INSERT OR IGNORE.
"""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.domain.access import (
    FEATURES,
    MENU_ITEMS,
    AuditLog,
    FeatureFlag,
    MenuItem,
    User,
)
from app.core.ports.admin import AdminStorePort


@contextmanager
def _connect(db_path: str | Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn) -> None:
    """Idempotent column migrations for pre-existing databases."""
    try:
        conn.execute("ALTER TABLE features ADD COLUMN roles TEXT NOT NULL DEFAULT 'admin,user'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteAdminStore(AdminStorePort):
    def __init__(self, db_path: str | Path | None = None):
        self._db = Path(db_path or settings.metadata_db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    username TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'admin',
                    status TEXT NOT NULL DEFAULT 'active',
                    password_hash TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS features (
                    key TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    group_name TEXT NOT NULL DEFAULT 'General',
                    roles TEXT NOT NULL DEFAULT 'admin,user'
                )
                """
            )
            _migrate(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS menus (
                    key TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    path TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    icon TEXT NOT NULL DEFAULT '',
                    position INTEGER NOT NULL DEFAULT 0,
                    feature TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS connection_logs (
                    id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    event TEXT NOT NULL,
                    ip TEXT NOT NULL DEFAULT '',
                    user_agent TEXT NOT NULL DEFAULT '',
                    device TEXT NOT NULL DEFAULT '',
                    browser TEXT NOT NULL DEFAULT '',
                    os TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_traffic (
                    id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status_code INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    ip TEXT NOT NULL DEFAULT '',
                    user_agent TEXT NOT NULL DEFAULT '',
                    device TEXT NOT NULL DEFAULT '',
                    browser TEXT NOT NULL DEFAULT '',
                    os TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            self._seed(conn)

    @staticmethod
    def _seed(conn) -> None:
        for feature in FEATURES:
            conn.execute(
                "INSERT INTO features (key, label, enabled, group_name, roles) VALUES (?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET roles=excluded.roles, "
                "label=excluded.label, group_name=excluded.group_name",
                (feature.key, feature.label, int(feature.enabled), feature.group, feature.roles),
            )
        for item in MENU_ITEMS:
            conn.execute(
                "INSERT INTO menus (key, label, path, group_name, icon, position, feature) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET "
                "label=excluded.label, path=excluded.path, group_name=excluded.group_name, "
                "icon=excluded.icon, position=excluded.position, feature=excluded.feature",
                (item.key, item.label, item.path, item.group, item.icon, item.order, item.feature),
            )
        known_features = tuple(f.key for f in FEATURES)
        known_menus = tuple(item.key for item in MENU_ITEMS)
        conn.execute(f"DELETE FROM features WHERE key NOT IN ({','.join('?' * len(known_features))})", known_features)
        conn.execute(f"DELETE FROM menus WHERE key NOT IN ({','.join('?' * len(known_menus))})", known_menus)
        for item in MENU_ITEMS:
            conn.execute(
                "INSERT OR IGNORE INTO menus (key, label, path, group_name, icon, position, feature) "
                "VALUES (?,?,?,?,?,?,?)",
                (item.key, item.label, item.path, item.group, item.icon, item.order, item.feature),
            )

    # ---------------------------------------------------------------- users
    def get_user_by_email(self, email: str):
        with _connect(self._db) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email=?", (str(email).strip().lower(),)
            ).fetchone()
        return _user_from_row(row) if row else None

    def get_user_by_id(self, user_id: str):
        with _connect(self._db) as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _user_from_row(row) if row else None

    def update_user(self, user_id: str, role: str | None = None, status: str | None = None,
                    name: str | None = None, username: str | None = None):
        with _connect(self._db) as conn:
            fields: dict[str, str] = {}
            if role is not None:
                fields["role"] = role
            if status is not None:
                fields["status"] = status
            if name is not None:
                fields["name"] = name
            if username is not None:
                fields["username"] = username
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE users SET {sets} WHERE id=?", (*fields.values(), user_id)
                )
        return self.get_user_by_id(user_id)

    def upsert_user(self, user) -> User:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO users (id, email, name, username, role, status, password_hash, created_at, last_login) "
                "VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(email) DO UPDATE SET name=excluded.name, username=excluded.username, "
                "role=excluded.role, status=excluded.status, password_hash=excluded.password_hash, "
                "last_login=excluded.last_login",
                (
                    user.id or uuid.uuid4().hex[:12],
                    user.email.strip().lower(),
                    user.name,
                    user.username,
                    user.role,
                    user.status,
                    user.password_hash,
                    user.created_at or _now(),
                    user.last_login,
                ),
            )
        return user

    def record_login(self, email: str) -> None:
        with _connect(self._db) as conn:
            conn.execute(
                "UPDATE users SET last_login=? WHERE email=?",
                (_now(), str(email).strip().lower()),
            )

    def list(self) -> list[User]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [_user_from_row(row) for row in rows]

    # -------------------------------------------------------------- features
    def list_features(self) -> list[FeatureFlag]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM features ORDER BY group_name, key").fetchall()
        return [
            FeatureFlag(
                key=r["key"],
                label=r["label"],
                enabled=bool(r["enabled"]),
                group=r["group_name"],
                roles=r["roles"] or "admin,user",
            )
            for r in rows
        ]

    def get_feature(self, key: str) -> FeatureFlag | None:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT * FROM features WHERE key=?", (key,)).fetchone()
        if not row:
            return None
        return FeatureFlag(
            key=row["key"], label=row["label"], enabled=bool(row["enabled"]),
            group=row["group_name"], roles=row["roles"] or "admin,user",
        )

    def set_feature(self, key: str, enabled: bool) -> FeatureFlag:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO features (key, label, enabled, group_name, roles) VALUES (?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET enabled=excluded.enabled",
                (key, key, int(enabled), "General", "admin,user"),
            )
        return self.get_feature(key)

    # ------------------------------------------------------------------ menus
    def list_menus(self) -> list[MenuItem]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM menus ORDER BY position").fetchall()
        return [
            MenuItem(
                key=r["key"],
                label=r["label"],
                path=r["path"],
                group=r["group_name"],
                icon=r["icon"],
                order=r["position"],
                feature=r["feature"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ audit
    def audit(self, user: str, action: str, target: str = "", detail: str = "") -> None:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO audit_logs (id, user, action, target, detail, created_at) VALUES (?,?,?,?,?,?)",
                (uuid.uuid4().hex[:12], user, action, target, detail, _now()),
            )

    def list_audit(self, limit: int = 50) -> list[AuditLog]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            AuditLog(
                id=r["id"],
                user=r["user"],
                action=r["action"],
                target=r["target"],
                detail=r["detail"],
                created_at=r["created_at"],
            )
            for r in rows
        ]


# ---------------------------------------------------------------- tracking
    def record_connection(self, user: str, event: str, ip: str = "", user_agent: str = "",
                          device: str = "", browser: str = "", os: str = "", location: str = "") -> None:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO connection_logs (id, user, event, ip, user_agent, device, browser, os, location, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (uuid.uuid4().hex[:14], user, event, ip, user_agent, device, browser, os, location, _now()),
            )

    def record_traffic(self, user: str, email: str, method: str, path: str, status: int,
                       duration_ms: int, ip: str = "", user_agent: str = "", device: str = "",
                       browser: str = "", os: str = "") -> None:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO api_traffic (id, user, email, method, path, status_code, duration_ms, "
                "ip, user_agent, device, browser, os, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (uuid.uuid4().hex[:14], user, email, method, path, status, duration_ms,
                 ip, user_agent, device, browser, os, _now()),
            )

    def list_traffic(self, limit: int = 200) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM api_traffic ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_connections(self, limit: int = 100) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM connection_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def traffic_stats(self) -> dict:
        with _connect(self._db) as conn:
            totals = conn.execute(
                "SELECT COUNT(*) AS requests, COALESCE(SUM(duration_ms),0) AS ms, "
                "COALESCE(AVG(duration_ms),0) AS avg FROM api_traffic"
            ).fetchone()
            by_status = conn.execute(
                "SELECT status_code, COUNT(*) AS c FROM api_traffic GROUP BY status_code"
            ).fetchall()
            by_user = conn.execute(
                "SELECT user, COUNT(*) AS c FROM api_traffic GROUP BY user ORDER BY c DESC LIMIT 8"
            ).fetchall()
            connections = conn.execute("SELECT COUNT(*) AS c FROM connection_logs").fetchone()
        return {
            "requests": int(totals["requests"]),
            "duration_ms": int(totals["ms"]),
            "avg_duration_ms": int(totals["avg"] or 0),
            "by_status": {str(r["status_code"]): int(r["c"]) for r in by_status},
            "top_users": [{"user": r["user"], "requests": int(r["c"])} for r in by_user],
            "connections": int(connections["c"]),
        }


def _user_from_row(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        username=row["username"] if "username" in row.keys() else "",
        role=row["role"],
        status=row["status"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        last_login=row["last_login"],
    )