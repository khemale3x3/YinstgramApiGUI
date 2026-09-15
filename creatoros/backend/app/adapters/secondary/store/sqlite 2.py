from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings
from app.core.domain.job import Job
from app.core.domain.project import Project
from app.core.ports.job_store import JobStorePort
from app.core.ports.project_store import ProjectStorePort


@contextmanager
def _connect(path: str | Path):
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class SqliteJobStore(JobStorePort):
    """Driven adapter: jobs persisted in creatoros/data/creatoros.db."""

    def __init__(self, db_path: str | Path | None = None):
        self._db = Path(db_path or settings.metadata_db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    project TEXT,
                    payload TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    current_step TEXT NOT NULL DEFAULT '',
                    steps TEXT NOT NULL DEFAULT '[]',
                    log TEXT NOT NULL DEFAULT '[]',
                    result TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN payload TEXT NOT NULL DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass

    def create(self, job: Job) -> Job:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO jobs (id, kind, project, payload, status, progress, current_step, "
                "steps, log, result, error, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    job.id, job.kind, job.project, json.dumps(job.payload),
                    job.status, job.progress,
                    job.current_step,
                    json.dumps(job.steps), json.dumps(job.log), json.dumps(job.result),
                    job.error, job.created_at, job.updated_at,
                ),
            )
        return job

    def update(self, job: Job) -> Job:
        with _connect(self._db) as conn:
            conn.execute(
                "UPDATE jobs SET kind=?, project=?, payload=?, status=?, progress=?, current_step=?, "
                "steps=?, log=?, result=?, error=?, created_at=?, updated_at=? WHERE id=?",
                (
                    job.kind, job.project, json.dumps(job.payload),
                    job.status, job.progress, job.current_step,
                    json.dumps(job.steps), json.dumps(job.log), json.dumps(job.result),
                    job.error, job.created_at, job.updated_at, job.id,
                ),
            )
        return job

    def get(self, job_id: str) -> Job | None:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return _job_from_row(row) if row else None

    def list(self, limit: int = 50) -> list[Job]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_job_from_row(row) for row in rows]

    def count_by_status(self) -> dict:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS c FROM jobs GROUP BY status").fetchall()
        return {row["status"]: int(row["c"]) for row in rows}

    def delete(self, job_id: str) -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        return cur.rowcount > 0

    def favorited(self, username: str) -> int:
        with _connect(self._db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM creator_favorites WHERE username=?", (username,)
            ).fetchone()
        return int(row[0] or 0)

    def favorite(self, username: str) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO creator_favorites (username, created_by, created_at) VALUES (?,?,?)",
                (username, "admin", __import__("datetime").datetime.now().isoformat()),
            )
        return {"saved": True}

    def unfavorite(self, username: str) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "DELETE FROM creator_favorites WHERE username=?",
                (username,),
            )
        return {"saved": False}

    def list_lists(self) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT name, created_by, created_at FROM creator_lists ORDER BY created_at DESC"
            ).fetchall()
        return [{"name": r[0], "created_by": r[1], "created_at": r[2]} for r in rows]

    def create_list(self, name: str, created_by: str = "admin") -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO creator_lists (name, created_by, created_at) VALUES (?,?,?)",
                (name, created_by, __import__("datetime").datetime.now().isoformat()),
            )
        return {"created": True}

    def add_to_list(self, list_name: str, username: str) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO creator_list_members (list_name, username, added_at) VALUES (?,?,?)",
                (list_name, username, __import__("datetime").datetime.now().isoformat()),
            )
        return {"added": True}

    def remove_from_list(self, list_name: str, username: str) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "DELETE FROM creator_list_members WHERE list_name=? AND username=?",
                (list_name, username),
            )
        return {"removed": True}

    def list_list_members(self, list_name: str) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT username, added_at FROM creator_list_members WHERE list_name=? ORDER BY added_at"
            ).fetchall()
        return [{"username": r[0], "added_at": r[1]} for r in rows]


class SqliteProjectStore(ProjectStorePort):
    """Driven adapter: projects + URL lists persisted in creatoros/data/creatoros.db."""

    def __init__(self, db_path: str | Path | None = None):
        self._db = Path(db_path or settings.metadata_db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    urls_pending INTEGER NOT NULL DEFAULT 0,
                    urls_done INTEGER NOT NULL DEFAULT 0,
                    creators_saved INTEGER NOT NULL DEFAULT 0,
                    outputs TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_urls (
                    project TEXT NOT NULL,
                    url TEXT NOT NULL,
                    state TEXT NOT NULL,          -- pending | done
                    processed_at TEXT,
                    PRIMARY KEY (project, url)
                )
                """
            )

    # ------------------------------------------------------------- projects
    def create(self, project: Project) -> Project:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects (name, status, urls_pending, urls_done, "
                "creators_saved, outputs, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    project.name, project.status, project.urls_pending, project.urls_done,
                    project.creators_saved, json.dumps(project.outputs),
                    project.created_at, project.updated_at,
                ),
            )
        return project

    def get(self, name: str) -> Project | None:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
        if not row:
            return None
        return self._refresh_from_urls(name, _project_from_row(row), conn=None)

    def update(self, project: Project) -> Project:
        with _connect(self._db) as conn:
            conn.execute(
                "UPDATE projects SET status=?, urls_pending=?, urls_done=?, creators_saved=?, "
                "outputs=?, updated_at=? WHERE name=?",
                (
                    project.status, project.urls_pending, project.urls_done,
                    project.creators_saved, json.dumps(project.outputs),
                    project.updated_at, project.name,
                ),
            )
        return project

    def list(self) -> list[Project]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        projects = [_project_from_row(row) for row in rows]
        result = []
        for project in projects:
            with _connect(self._db) as conn:
                project = self._apply_counts(project, conn)
            result.append(project)
        return result

    def delete(self, name: str) -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute("DELETE FROM projects WHERE name=?", (name,))
            conn.execute("DELETE FROM project_urls WHERE project=?", (name,))
        return cur.rowcount > 0

    # ---------------------------------------------------------------- urls
    def pending_urls(self, name: str) -> list[str]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT url FROM project_urls WHERE project=? AND state='pending' ORDER BY rowid",
                (name,),
            ).fetchall()
        return [r["url"] for r in rows]

    def done_urls(self, name: str) -> list[str]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT url FROM project_urls WHERE project=? AND state='done' ORDER BY rowid",
                (name,),
            ).fetchall()
        return [r["url"] for r in rows]

    def add_urls(self, name: str, urls: list[str], done: bool = False) -> int:
        state = "done" if done else "pending"
        added = 0
        with _connect(self._db) as conn:
            for url in urls:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO project_urls (project, url, state) VALUES (?,?,?)",
                    (name, url, state),
                )
                added += cur.rowcount
        return added

    def remove_pending(self, name: str, urls: list[str]) -> int:
        removed = 0
        with _connect(self._db) as conn:
            for url in urls:
                cur = conn.execute(
                    "DELETE FROM project_urls WHERE project=? AND url=? AND state='pending'",
                    (name, url),
                )
                removed += cur.rowcount
        return removed

    def mark_done(self, name: str, url: str) -> bool:
        from datetime import datetime, timezone

        with _connect(self._db) as conn:
            cur = conn.execute(
                "UPDATE project_urls SET state='done', processed_at=? "
                "WHERE project=? AND url=? AND state='pending'",
                (datetime.now(timezone.utc).isoformat(), name, url),
            )
            moved_any = cur.rowcount > 0
            if not moved_any:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO project_urls (project, url, state, processed_at) VALUES (?,?,?,?)",
                    (name, url, "done", datetime.now(timezone.utc).isoformat()),
                )
                moved_any = cur.rowcount > 0
        return moved_any

    # ------------------------------------------------------------- internal
    def _apply_counts(self, project: Project, conn) -> Project:
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM project_urls WHERE project=? AND state='pending'", (project.name,)
        ).fetchone()["c"]
        done = conn.execute(
            "SELECT COUNT(*) AS c FROM project_urls WHERE project=? AND state='done'", (project.name,)
        ).fetchone()["c"]
        project.urls_pending, project.urls_done = int(pending), int(done)
        return project

    def _refresh_from_urls(self, name: str, project: Project, conn) -> Project:
        if conn is None:
            with _connect(self._db) as conn:
                return self._apply_counts(project, conn)
        return self._apply_counts(project, conn)


def _job_from_row(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        kind=row["kind"],
        project=row["project"],
        payload=json.loads(row["payload"] or "{}"),
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


def _project_from_row(row: sqlite3.Row) -> Project:
    return Project(
        name=row["name"],
        status=row["status"],
        urls_pending=row["urls_pending"],
        urls_done=row["urls_done"],
        creators_saved=row["creators_saved"],
        outputs=json.loads(row["outputs"] or "[]"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )