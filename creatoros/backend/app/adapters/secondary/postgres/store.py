"""PostgreSQL driven adapters for the CreatorOS app store.

Implements the same ports as the SQLite adapters (jobs, projects, RBAC/admin
and profile metadata) against the configured PostgreSQL database (default:
localhost:5432 / yinstagram / schema creatoros). All DDL is provisioned by
connection.init_schema() using data/postgres/*.sql.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.adapters.secondary.postgres.connection import pg_connect, pg_cursor
from app.core.domain.access import FEATURES, MENU_ITEMS, AuditLog, FeatureFlag, MenuItem, User
from app.core.domain.campaign import Campaign, CampaignCreator, CampaignRequest
from app.core.domain.job import Job
from app.core.domain.project import Project
from app.core.ports.admin import AdminStorePort
from app.core.ports.campaign import CampaignStorePort
from app.core.ports.database import DatabasePort
from app.core.ports.job_store import JobStorePort
from app.core.ports.project_store import ProjectStorePort


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------- jobs
class PgJobStore(JobStorePort):
    def create(self, job: Job) -> Job:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.jobs (id, kind, project, payload, status, progress, "
                    "current_step, steps, log, result, error, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        job.id, job.kind, job.project, json.dumps(job.payload),
                        job.status, job.progress,
                        job.current_step, json.dumps(job.steps), json.dumps(job.log),
                        json.dumps(job.result), job.error, job.created_at, job.updated_at,
                    ),
                )
        return job

    def update(self, job: Job) -> Job:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.jobs SET kind=%s, project=%s, payload=%s, status=%s, progress=%s, "
                    "current_step=%s, steps=%s, log=%s, result=%s, error=%s, created_at=%s, "
                    "updated_at=%s WHERE id=%s",
                    (
                        job.kind, job.project, json.dumps(job.payload), job.status, job.progress,
                        job.current_step,
                        json.dumps(job.steps), json.dumps(job.log), json.dumps(job.result),
                        job.error, job.created_at, job.updated_at, job.id,
                    ),
                )
        return job

    def get(self, job_id: str) -> Job | None:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
        return _job_from_row(row) if row else None

    def list(self, limit: int = 50) -> list[Job]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.jobs ORDER BY created_at DESC LIMIT %s", (int(limit),)
            )
            rows = cur.fetchall()
        return [_job_from_row(row) for row in rows]

    def count_by_status(self) -> dict:
        with pg_cursor() as cur:
            cur.execute("SELECT status, COUNT(*) AS c FROM creatoros.jobs GROUP BY status")
            rows = cur.fetchall()
        return {row["status"]: int(row["c"]) for row in rows}

    def delete(self, job_id: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM creatoros.jobs WHERE id=%s", (job_id,))
                return cur.rowcount > 0


# ------------------------------------------------------------------ projects
class PgProjectStore(ProjectStorePort):
    PROJECT_COUNT_SQL = """
        SELECT p.*,
               COALESCE(SUM(CASE WHEN u.state = 'pending' THEN 1 ELSE 0 END), 0) AS pending_count,
               COALESCE(SUM(CASE WHEN u.state = 'done'    THEN 1 ELSE 0 END), 0) AS done_count
        FROM creatoros.projects p
        LEFT JOIN creatoros.project_urls u ON u.project = p.name
    """

    def create(self, project: Project) -> Project:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.projects (name, status, urls_pending, urls_done, "
                    "creators_saved, outputs, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (name) DO UPDATE SET status=EXCLUDED.status, "
                    "urls_pending=EXCLUDED.urls_pending, urls_done=EXCLUDED.urls_done, "
                    "creators_saved=EXCLUDED.creators_saved, outputs=EXCLUDED.outputs, "
                    "updated_at=EXCLUDED.updated_at",
                    (
                        project.name, project.status, project.urls_pending, project.urls_done,
                        project.creators_saved, json.dumps(project.outputs),
                        project.created_at, project.updated_at,
                    ),
                )
        return project

    def get(self, name: str) -> Project | None:
        where = " WHERE p.name = %s"
        with pg_cursor() as cur:
            cur.execute(
                self.PROJECT_COUNT_SQL + where + " GROUP BY p.name LIMIT 1", (name,)
            )
            row = cur.fetchone()
        return _project_from_row(row) if row else None

    def update(self, project: Project) -> Project:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.projects SET status=%s, urls_pending=%s, urls_done=%s, "
                    "creators_saved=%s, outputs=%s, updated_at=%s WHERE name=%s",
                    (
                        project.status, project.urls_pending, project.urls_done,
                        project.creators_saved, json.dumps(project.outputs),
                        project.updated_at, project.name,
                    ),
                )
        return project

    def list(self) -> list[Project]:
        with pg_cursor() as cur:
            cur.execute(
                self.PROJECT_COUNT_SQL
                + " GROUP BY p.name ORDER BY p.created_at DESC"
            )
            rows = cur.fetchall()
        return [_project_from_row(row) for row in rows]

    def delete(self, name: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM creatoros.projects WHERE name=%s", (name,))
                deleted = cur.rowcount > 0
                cur.execute("DELETE FROM creatoros.project_urls WHERE project=%s", (name,))
                return deleted

    # ---------------------------------------------------------------- urls
    def pending_urls(self, name: str) -> list[str]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT url FROM creatoros.project_urls WHERE project=%s AND state='pending' ORDER BY url",
                (name,),
            )
            return [r["url"] for r in cur.fetchall()]

    def done_urls(self, name: str) -> list[str]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT url FROM creatoros.project_urls WHERE project=%s AND state='done' ORDER BY url",
                (name,),
            )
            return [r["url"] for r in cur.fetchall()]

    def add_urls(self, name: str, urls: list[str], done: bool = False) -> int:
        state = "done" if done else "pending"
        added = 0
        with pg_connect() as conn:
            with conn.cursor() as cur:
                for url in urls:
                    cur.execute(
                        "INSERT INTO creatoros.project_urls (project, url, state) VALUES (%s,%s,%s) "
                        "ON CONFLICT (project, url) DO NOTHING",
                        (name, url, state),
                    )
                    added += cur.rowcount
        return added

    def remove_pending(self, name: str, urls: list[str]) -> int:
        removed = 0
        with pg_connect() as conn:
            with conn.cursor() as cur:
                for url in urls:
                    cur.execute(
                        "DELETE FROM creatoros.project_urls WHERE project=%s AND url=%s AND state='pending'",
                        (name, url),
                    )
                    removed += cur.rowcount
        return removed

    def mark_done(self, name: str, url: str) -> bool:
        processed = _now()
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.project_urls SET state='done', processed_at=%s "
                    "WHERE project=%s AND url=%s AND state='pending'",
                    (processed, name, url),
                )
                moved_any = cur.rowcount > 0
                if not moved_any:
                    cur.execute(
                        "INSERT INTO creatoros.project_urls (project, url, state, processed_at) "
                        "VALUES (%s,%s,%s,%s) ON CONFLICT (project, url) DO NOTHING",
                        (name, url, "done", processed),
                    )
                    moved_any = cur.rowcount > 0
        return moved_any


# ---------------------------------------------------------------- admin/rbac
class PgAdminStore(AdminStorePort):
    def __init__(self):
        with pg_connect() as conn:
            with conn.cursor() as cur:
                for feature in FEATURES:
                    cur.execute(
                        "INSERT INTO creatoros.features (key, label, enabled, group_name, roles) "
                        "VALUES (%s,%s,%s,%s,%s) "
                        "ON CONFLICT (key) DO UPDATE SET roles=EXCLUDED.roles, "
                        "label=EXCLUDED.label, group_name=EXCLUDED.group_name",
                        (feature.key, feature.label, feature.enabled, feature.group, feature.roles),
                    )
                for item in MENU_ITEMS:
                    cur.execute(
                        "INSERT INTO creatoros.menus (key, label, path, group_name, icon, \"position\", feature) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (key) DO UPDATE SET "
                        "label=EXCLUDED.label, path=EXCLUDED.path, group_name=EXCLUDED.group_name, "
                        "icon=EXCLUDED.icon, \"position\"=EXCLUDED.\"position\", feature=EXCLUDED.feature",
                        (item.key, item.label, item.path, item.group, item.icon, item.order, item.feature),
                    )
                cur.execute(
                    "DELETE FROM creatoros.features WHERE key <> ALL(%s)",
                    ([f.key for f in FEATURES],),
                )
                cur.execute(
                    "DELETE FROM creatoros.menus WHERE key <> ALL(%s)",
                    ([item.key for item in MENU_ITEMS],),
                )

    # ---------------------------------------------------------------- users
    def get_user_by_email(self, email: str):
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.users WHERE email=%s", (str(email).strip().lower(),))
            row = cur.fetchone()
        return _user_from_row(row) if row else None

    def get_user_by_id(self, user_id: str):
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.users WHERE id=%s", (user_id,))
            row = cur.fetchone()
        return _user_from_row(row) if row else None

    def update_user(self, user_id: str, role: str | None = None, status: str | None = None,
                    name: str | None = None, username: str | None = None):
        with pg_connect() as conn:
            with conn.cursor() as cur:
                fields: list[str] = []
                values: list = []
                for key, value in (("role", role), ("status", status), ("name", name), ("username", username)):
                    if value is not None:
                        fields.append(f"{key}=%s")
                        values.append(value)
                if fields:
                    cur.execute(
                        f"UPDATE creatoros.users SET {', '.join(fields)} WHERE id=%s",
                        (*values, user_id),
                    )
        return self.get_user_by_id(user_id)

    def upsert_user(self, user) -> User:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.users (id, email, name, username, role, status, password_hash, created_at, last_login) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (email) DO UPDATE SET name=EXCLUDED.name, username=EXCLUDED.username, "
                    "role=EXCLUDED.role, status=EXCLUDED.status, password_hash=EXCLUDED.password_hash, "
                    "last_login=EXCLUDED.last_login",
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
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.users SET last_login=%s WHERE email=%s",
                    (_now(), str(email).strip().lower()),
                )

    def list(self) -> list[User]:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.users ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [_user_from_row(row) for row in rows]

    # -------------------------------------------------------------- features
    def list_features(self) -> list[FeatureFlag]:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.features ORDER BY group_name, key")
            rows = cur.fetchall()
        return [
            FeatureFlag(
                key=r["key"], label=r["label"], enabled=bool(r["enabled"]),
                group=r["group_name"], roles=r["roles"] or "admin,user",
            )
            for r in rows
        ]

    def get_feature(self, key: str) -> FeatureFlag | None:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.features WHERE key=%s", (key,))
            row = cur.fetchone()
        if not row:
            return None
        return FeatureFlag(
            key=row["key"], label=row["label"], enabled=bool(row["enabled"]),
            group=row["group_name"], roles=row["roles"] or "admin,user",
        )

    def set_feature(self, key: str, enabled: bool) -> FeatureFlag:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.features (key, label, enabled, group_name, roles) "
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (key) DO UPDATE SET enabled=EXCLUDED.enabled",
                    (key, key, enabled, "General", "admin,user"),
                )
        return self.get_feature(key)

    # ------------------------------------------------------------------ menus
    def list_menus(self) -> list[MenuItem]:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.menus ORDER BY position")
            rows = cur.fetchall()
        return [
            MenuItem(
                key=r["key"], label=r["label"], path=r["path"], group=r["group_name"],
                icon=r["icon"], order=r["position"], feature=r["feature"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ audit
    def audit(self, user: str, action: str, target: str = "", detail: str = "") -> None:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CALL creatoros.record_audit(%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex[:12], user, action, target, detail, _now()),
                )

    def list_audit(self, limit: int = 50) -> list[AuditLog]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.audit_logs ORDER BY created_at DESC LIMIT %s", (int(limit),)
            )
            rows = cur.fetchall()
        return [
            AuditLog(
                id=r["id"], user=r["user"], action=r["action"], target=r["target"],
                detail=r["detail"], created_at=r["created_at"],
            )
            for r in rows
        ]


# ---------------------------------------------------------------- tracking
    def record_connection(self, user: str, event: str, ip: str = "", user_agent: str = "",
                          device: str = "", browser: str = "", os: str = "", location: str = "") -> None:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.connection_logs (id, \"user\", event, ip, user_agent, "
                    "device, browser, os, location, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex[:14], user, event, ip, user_agent, device, browser, os, location, _now()),
                )

    def record_traffic(self, user: str, email: str, method: str, path: str, status: int,
                       duration_ms: int, ip: str = "", user_agent: str = "", device: str = "",
                       browser: str = "", os: str = "") -> None:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.api_traffic (id, \"user\", email, method, path, status_code, "
                    "duration_ms, ip, user_agent, device, browser, os, created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex[:14], user, email, method, path, status, duration_ms,
                     ip, user_agent, device, browser, os, _now()),
                )

    def list_traffic(self, limit: int = 200) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.api_traffic ORDER BY created_at DESC LIMIT %s", (int(limit),)
            )
            return [dict(r) for r in cur.fetchall()]

    def list_connections(self, limit: int = 100) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.connection_logs ORDER BY created_at DESC LIMIT %s", (int(limit),)
            )
            return [dict(r) for r in cur.fetchall()]

    def favorited(self, username: str) -> int:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM creatoros.creator_favorites WHERE username=%s",
                (username,),
            )
            row = cur.fetchone()
        return int(row["count"] or 0)

    def favorite(self, username: str) -> dict:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.creator_favorites (username, created_by, created_at) VALUES (%s,%s,%s) ON CONFLICT (username, created_by) DO NOTHING",
                    (username, "admin", __import__("datetime").datetime.now(timezone.utc).isoformat()),
                )
        return {"saved": True}

    def unfavorite(self, username: str) -> dict:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM creatoros.creator_favorites WHERE username=%s",
                    (username,),
                )
        return {"saved": False}

    def list_lists(self) -> list[dict]:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name, created_by, created_at FROM creatoros.creator_lists ORDER BY created_at DESC"
                )
                rows = cur.fetchall()
        return [{"name": r[0], "created_by": r[1], "created_at": r[2]} for r in rows]

    def create_list(self, name: str, created_by: str = "admin") -> dict:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.creator_lists (name, created_by, created_at) VALUES (%s,%s,%s) ON CONFLICT (name) DO NOTHING",
                    (name, created_by, __import__("datetime").datetime.now(timezone.utc).isoformat()),
                )
        return {"created": True}

    def add_to_list(self, list_name: str, username: str) -> dict:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.creator_list_members (list_name, username, added_at) VALUES (%s,%s,%s) ON CONFLICT (list_name, username) DO NOTHING",
                    (list_name, username, __import__("datetime").datetime.now(timezone.utc).isoformat()),
                )
        return {"added": True}

    def remove_from_list(self, list_name: str, username: str) -> dict:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM creatoros.creator_list_members WHERE list_name=%s AND username=%s",
                    (list_name, username),
                )
        return {"removed": True}

    def list_list_members(self, list_name: str) -> list[dict]:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT username, added_at FROM creatoros.creator_list_members WHERE list_name=%s ORDER BY added_at"
                )
                rows = cur.fetchall()
        return [{"username": r[0], "added_at": r[1]} for r in rows]

    def traffic_stats(self) -> dict:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS requests, COALESCE(SUM(duration_ms),0) AS ms, "
                "COALESCE(AVG(duration_ms),0) AS avg FROM creatoros.api_traffic"
            )
            totals = cur.fetchone()
            cur.execute(
                "SELECT status_code, COUNT(*) AS c FROM creatoros.api_traffic GROUP BY status_code"
            )
            by_status = cur.fetchall()
            cur.execute(
                "SELECT \"user\", COUNT(*) AS c FROM creatoros.api_traffic GROUP BY \"user\" \
                ORDER BY c DESC LIMIT 8"
            )
            by_user = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS c FROM creatoros.connection_logs")
            connections = cur.fetchone()
        return {
            "requests": int(totals["requests"]),
            "duration_ms": int(totals["ms"]),
            "avg_duration_ms": int(totals["avg"] or 0),
            "by_status": {str(r["status_code"]): int(r["c"]) for r in by_status},
            "top_users": [{"user": r["user"], "requests": int(r["c"])} for r in by_user],
            "connections": int(connections["c"]),
        }


# ------------------------------------------------------------ profile store
class PgProfileStore(DatabasePort):
    @property
    def name(self) -> str:
        return "postgres-scraper"

    def available(self) -> bool:
        try:
            with pg_cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM creatoros.profiles")
                cur.fetchone()
            return True
        except Exception:
            return False

    def status(self) -> dict:
        try:
            ok = self.available()
            return {
                "available": ok,
                "type": "postgres",
                "database": f"{settings.pg_name}/{settings.pg_schema}",
                "profiles": self.count_profiles() if ok else 0,
            }
        except Exception as exc:
            return {"available": False, "type": "postgres", "error": str(exc)}

    def save_profile(self, username, url, profile_info, post_info, stats=None) -> bool:
        from datetime import datetime

        followers = following = media_count = 0
        is_private = is_verified = False
        full_name = biography = category = profile_pic_url = ""
        try:
            user = profile_info.get("data", {}).get("user", {})
            if isinstance(user.get("data"), dict):
                user = user["data"]
            followers = user.get("follower_count") or 0
            following = user.get("following_count") or 0
            media_count = user.get("media_count") or 0
            is_private = bool(user.get("is_private", False))
            is_verified = bool(user.get("is_verified", False))
            full_name = user.get("full_name") or ""
            biography = user.get("biography") or ""
            category = user.get("category_name") or ""
            profile_pic_url = user.get("profile_pic_url_hd") or user.get("profile_pic_url") or ""
        except Exception:
            pass

        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CALL creatoros.upsert_profile(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        username.strip().lstrip("@"), url,
                        json.dumps(profile_info, ensure_ascii=False),
                        json.dumps(post_info, ensure_ascii=False),
                        followers, following, media_count,
                        is_private, is_verified, full_name, biography, category,
                        profile_pic_url, datetime.now().isoformat(),
                    ),
                )
        return True

    def get_profile(self, username) -> dict | None:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.profiles WHERE username=%s",
                (username.strip().lstrip("@"),),
            )
            row = cur.fetchone()
        return _row_to_profile(row) if row else None

    def search_profiles(self, query, limit=20, offset=0) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                """
                SELECT username, url, followers, following, media_count, is_private,
                       is_verified, full_name, biography, category, profile_pic_url,
                       scraped_at, profile_info, post_info
                FROM creatoros.profiles
                WHERE username ILIKE '%%' || %s || '%%'
                   OR full_name  ILIKE '%%' || %s || '%%'
                   OR biography  ILIKE '%%' || %s || '%%'
                   OR category   ILIKE '%%' || %s || '%%'
                ORDER BY scraped_at DESC LIMIT %s OFFSET %s
                """,
                (str(query).strip(), str(query).strip(), str(query).strip(), str(query).strip(),
                 int(limit), int(offset)),
            )
            rows = cur.fetchall()
        return [_row_to_profile(row) for row in rows]

    def count_search(self, query: str) -> int | None:
        with pg_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM creatoros.profiles
                WHERE username ILIKE '%%' || %s || '%%'
                   OR full_name  ILIKE '%%' || %s || '%%'
                   OR biography  ILIKE '%%' || %s || '%%'
                   OR category   ILIKE '%%' || %s || '%%'
                """,
                (str(query).strip(), str(query).strip(), str(query).strip(), str(query).strip()),
            )
            row = cur.fetchone()
        return int(row["c"] or 0)

    def count_profiles(self) -> int:
        with pg_cursor() as cur:
            cur.execute("SELECT creatoros.count_profiles() AS c")
            row = cur.fetchone()
        return int(row["c"] or 0)

    def sum_media_count(self) -> int:
        with pg_cursor() as cur:
            cur.execute("SELECT creatoros.sum_media_count() AS total")
            row = cur.fetchone()
        return int(row["total"] or 0)

    def top_profiles(self, limit: int = 10, offset: int = 0) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.profiles ORDER BY followers DESC LIMIT %s OFFSET %s",
                (int(limit), int(offset)),
            )
            rows = cur.fetchall()
        return [_row_to_profile(row) for row in rows]

    def list_recent(self, limit=20) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.profiles ORDER BY scraped_at DESC LIMIT %s", (int(limit),)
            )
            rows = cur.fetchall()
        return [_row_to_profile(row) for row in rows]

    def profile_growth(self, days: int = 14) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT day, c FROM ("
                "  SELECT to_char(scraped_at::date, 'YYYY-MM-DD') AS day, COUNT(*) AS c "
                "  FROM creatoros.profiles WHERE scraped_at IS NOT NULL "
                "  GROUP BY day ORDER BY day DESC LIMIT %s"
                ") t ORDER BY day ASC",
                (int(days),),
            )
            rows = cur.fetchall()
        return [{"date": row["day"], "count": int(row["c"] or 0)} for row in rows]

    def list_tables(self) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'creatoros' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            names = [r["table_name"] for r in cur.fetchall()]
            tables = []
            for name in names:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'creatoros' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (name,),
                )
                cols = [
                    {
                        "name": r["column_name"],
                        "type": r["data_type"],
                        "nullable": r["is_nullable"] == "YES",
                    }
                    for r in cur.fetchall()
                ]
                cur.execute(f"SELECT COUNT(*) AS c FROM creatoros.{name}")
                rows = int(cur.fetchone()["c"] or 0)
                tables.append({"name": name, "columns": cols, "rows": rows})
        return tables

    def list_views(self) -> list[dict]:
        """Introspect the creatoros read-model views (real PG views)."""
        view_cols = {
            "v_dashboard_stats": ["creators", "posts_analyzed", "jobs_running"],
            "v_jobs_by_status": ["status", "cnt"],
            "v_recent_activity": ["user", "action", "target", "created_at"],
            "v_profiles_by_followers": [
                "username", "followers", "media_count", "category", "scraped_at",
            ],
            "v_profiles_by_category": ["category", "creators", "avg_followers"],
            "v_engagement_insights": ["username", "followers", "following", "media_count", "content_per_1k_followers"],
        }
        views: list[dict] = []
        for name, cols in view_cols.items():
            try:
                with pg_cursor() as cur:
                    cur.execute(f'SELECT * FROM creatoros.{name} LIMIT 5')
                    rows = cur.fetchall()
                    col_names = [d[0] for d in cur.description] if cur.description else cols
                views.append(
                    {
                        "name": name,
                        "columns": col_names,
                        "rows": len(rows),
                        "sample": [dict(r) for r in rows],
                    }
                )
            except Exception as exc:  # noqa: BLE001 - a missing view shouldn't break the inspector
                views.append({"name": name, "error": str(exc), "columns": cols, "rows": 0, "sample": []})
        return views

    # ------------------------------------------------------------ marketplace
    def upsert_profile(self, record: dict) -> bool:
        from datetime import datetime

        username = str(record.get("username") or "").strip().lstrip("@")
        if not username:
            return False
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CALL creatoros.upsert_profile(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        username,
                        str(record.get("url") or f"https://www.instagram.com/{username}/"),
                        json.dumps({"marketplace": True}, ensure_ascii=False),
                        json.dumps({}, ensure_ascii=False),
                        int(record.get("followers") or 0),
                        int(record.get("following") or 0),
                        int(record.get("media_count") or 0),
                        bool(record.get("is_private")),
                        bool(record.get("is_verified")),
                        str(record.get("full_name") or ""),
                        str(record.get("biography") or ""),
                        str(record.get("category") or ""),
                        str(record.get("profile_pic_url") or ""),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        return True

    def count_profiles_by_category(self, category: str) -> int:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM creatoros.profiles WHERE category ILIKE %s",
                (f"%{category.strip()}%",),
            )
            row = cur.fetchone()
        return int(row["c"] or 0)

    def search_profiles_by_category(self, category: str, limit: int = 50) -> list[dict]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.profiles WHERE category ILIKE %s "
                "ORDER BY followers DESC LIMIT %s",
                (f"%{category.strip()}%", int(limit)),
            )
            rows = cur.fetchall()
        return [_row_to_profile(row) for row in rows]

    def ingest_from_keylist(self, keylist_path, on_event=None, table=None):
        raise NotImplementedError("PostgreSQL store has no SQL Server ingest")


# ------------------------------------------------------------------ mappers
def _job_from_row(row) -> Job:
    payload = json.loads(row["payload"]) if row.get("payload") else {}
    return Job(
        id=row["id"],
        kind=row["kind"],
        project=row["project"],
        payload=payload,
        status=row["status"],
        progress=row["progress"],
        current_step=row["current_step"],
        steps=json.loads(row["steps"] or "[]"),
        log=json.loads(row["log"] or "[]"),
        result=json.loads(row["result"] or "{}"),
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _project_from_row(row) -> Project:
    return Project(
        name=row["name"],
        status=row["status"],
        urls_pending=int(row.get("pending_count") or row["urls_pending"]),
        urls_done=int(row.get("done_count") or row["urls_done"]),
        creators_saved=row["creators_saved"],
        outputs=json.loads(row["outputs"] or "[]"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _user_from_row(row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        username=row.get("username", "") if isinstance(row, dict) else "",
        role=row["role"],
        status=row["status"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        last_login=row["last_login"],
    )


def _row_to_profile(row) -> dict:
    return {
        "username": row["username"],
        "url": row["url"],
        "followers": row["followers"],
        "following": row["following"],
        "media_count": row["media_count"],
        "is_private": bool(row["is_private"]),
        "is_verified": bool(row["is_verified"]),
        "full_name": row["full_name"],
        "biography": row["biography"],
        "category": row["category"],
        "profile_pic_url": row["profile_pic_url"],
        "scraped_at": row["scraped_at"],
        "has_profile_info": bool(row["profile_info"]),
        "has_post_info": bool(row["post_info"]),
    }


def _row_to_campaign(row) -> Campaign:
    return Campaign(
        id=row["id"],
        name=row["name"],
        budget_min=row["budget_min"],
        budget_max=row["budget_max"],
        target_count=row["target_count"],
        location=row["location"],
        audience=row["audience"],
        min_engagement=row["min_engagement"],
        status=row["status"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        requested_by=row.get("requested_by", ""),
        requested_at=row.get("requested_at", ""),
        reviewed_by=row.get("reviewed_by", ""),
        reviewed_at=row.get("reviewed_at", ""),
        decision=row.get("decision", ""),
        comment=row.get("comment", ""),
    )


def _row_to_campaign_creator(row) -> CampaignCreator:
    return CampaignCreator(
        id=row["id"],
        campaign_id=row["campaign_id"],
        creator_username=row["creator_username"],
        score=row["score"],
        match_pct=row["match_pct"],
        rank=row["rank"],
        status=row["status"],
        followers=row["followers"],
        full_name=row["full_name"],
        category=row["category"],
        location=row["location"],
        biography=row["biography"],
        engagement=row["engagement"],
        created_at=row["created_at"],
    )


def _row_to_campaign_request(row) -> CampaignRequest:
    return CampaignRequest(
        id=row["id"],
        campaign_id=row["campaign_id"],
        creator_username=row["creator_username"],
        status=row["status"],
        message=row["message"],
        created_at=row["created_at"],
    )


# ------------------------------------------------------------------- campaigns
class PgCampaignStore(CampaignStorePort):
    def create_campaign(self, campaign: Campaign) -> Campaign:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.campaigns (id, name, budget_min, budget_max, target_count, "
                    "location, audience, min_engagement, status, notes, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (campaign.id, campaign.name, campaign.budget_min, campaign.budget_max,
                     campaign.target_count, campaign.location, campaign.audience,
                     campaign.min_engagement, campaign.status, campaign.notes,
                     campaign.created_at, campaign.updated_at),
                )
        return campaign

    def update_campaign(self, campaign: Campaign) -> Campaign:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.campaigns SET name=%s, budget_min=%s, budget_max=%s, "
                    "target_count=%s, location=%s, audience=%s, min_engagement=%s, status=%s, "
                    "notes=%s, requested_by=%s, requested_at=%s, reviewed_by=%s, reviewed_at=%s, "
                    "decision=%s, comment=%s, updated_at=%s WHERE id=%s",
                    (campaign.name, campaign.budget_min, campaign.budget_max, campaign.target_count,
                     campaign.location, campaign.audience, campaign.min_engagement, campaign.status,
                     campaign.notes, campaign.requested_by, campaign.requested_at,
                     campaign.reviewed_by, campaign.reviewed_at, campaign.decision, campaign.comment,
                     campaign.updated_at, campaign.id),
                )
        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with pg_cursor() as cur:
            cur.execute("SELECT * FROM creatoros.campaigns WHERE id=%s", (campaign_id,))
            row = cur.fetchone()
        return _row_to_campaign(row) if row else None

    def list_campaigns(self) -> list[Campaign]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.campaigns ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [_row_to_campaign(row) for row in rows]

    def delete_campaign(self, campaign_id: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM creatoros.campaign_creators WHERE campaign_id=%s", (campaign_id,))
                cur.execute("DELETE FROM creatoros.campaign_requests WHERE campaign_id=%s", (campaign_id,))
                cur.execute("DELETE FROM creatoros.campaigns WHERE id=%s", (campaign_id,))
                deleted = cur.rowcount
        return deleted > 0

    def campaign_stats(self) -> dict:
        with pg_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM creatoros.campaigns")
            total = int(cur.fetchone()["total"])
            cur.execute(
                "SELECT status, COUNT(*) AS n FROM creatoros.campaigns GROUP BY status"
            )
            by_status = {r["status"]: int(r["n"]) for r in cur.fetchall()}
            cur.execute("SELECT COUNT(*) AS c FROM creatoros.campaign_creators")
            matches = int(cur.fetchone()["c"])
        return {"total": total, "by_status": by_status, "matches": matches}

    def replace_creators(self, campaign_id: str, rows: list[CampaignCreator]) -> None:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM creatoros.campaign_creators WHERE campaign_id=%s", (campaign_id,)
                )
                for row in rows:
                    cur.execute(
                        "INSERT INTO creatoros.campaign_creators (id, campaign_id, creator_username, "
                        "score, match_pct, rank, status, followers, full_name, category, location, "
                        "biography, engagement, created_at) VALUES "
                        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (row.id, campaign_id, row.creator_username, row.score, row.match_pct,
                         row.rank, row.status, row.followers, row.full_name, row.category,
                         row.location, row.biography, row.engagement, row.created_at),
                    )

    def list_creators(self, campaign_id: str) -> list[CampaignCreator]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.campaign_creators WHERE campaign_id=%s ORDER BY rank",
                (campaign_id,),
            )
            rows = cur.fetchall()
        return [_row_to_campaign_creator(row) for row in rows]

    def add_creator(self, row: CampaignCreator) -> CampaignCreator:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.campaign_creators (id, campaign_id, creator_username, "
                    "score, match_pct, rank, status, followers, full_name, category, location, "
                    "biography, engagement, created_at) VALUES "
                    "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                    (row.id, row.campaign_id, row.creator_username, row.score, row.match_pct,
                     row.rank, row.status, row.followers, row.full_name, row.category,
                     row.location, row.biography, row.engagement, row.created_at),
                )
        return row

    def remove_creator(self, campaign_id: str, username: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM creatoros.campaign_creators WHERE campaign_id=%s AND creator_username=%s",
                    (campaign_id, username),
                )
                deleted = cur.rowcount
        return deleted > 0

    def set_creator_status(self, campaign_id: str, username: str, status: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.campaign_creators SET status=%s "
                    "WHERE campaign_id=%s AND creator_username=%s",
                    (status, campaign_id, username),
                )
                updated = cur.rowcount
        return updated > 0

    def list_requests(self, campaign_id: str) -> list[CampaignRequest]:
        with pg_cursor() as cur:
            cur.execute(
                "SELECT * FROM creatoros.campaign_requests WHERE campaign_id=%s ORDER BY created_at DESC",
                (campaign_id,),
            )
            rows = cur.fetchall()
        return [_row_to_campaign_request(row) for row in rows]

    def add_request(self, request: CampaignRequest) -> CampaignRequest:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO creatoros.campaign_requests (id, campaign_id, creator_username, "
                    "status, message, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (request.id, request.campaign_id, request.creator_username,
                     request.status, request.message, request.created_at),
                )
        return request

    def set_request_status(self, campaign_id: str, username: str, status: str) -> bool:
        with pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.campaign_requests SET status=%s "
                    "WHERE campaign_id=%s AND creator_username=%s",
                    (status, campaign_id, username),
                )
                updated = cur.rowcount
        return updated > 0