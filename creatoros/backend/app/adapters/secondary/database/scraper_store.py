"""Local metadata store — SQLite scraper_data.db (profiles table).

Persists scraped profiles the same way the user's iteration01scraper.py does
(connect_db / ensure_db_tables / save_scrape_to_db), so existing pipelines and
CreatorOS share one database.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings
from app.core.ports.database import DatabasePort


@contextmanager
def _connect(db_path: str | Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class ScraperSqliteAdapter(DatabasePort):
    """Driven adapter: local SQLite profile metadata store."""

    def __init__(self, db_path: str | Path | None = None):
        self._db = Path(db_path or settings.scraper_db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    username TEXT PRIMARY KEY,
                    url TEXT,
                    profile_info TEXT,
                    post_info TEXT,
                    followers INTEGER DEFAULT 0,
                    following INTEGER DEFAULT 0,
                    media_count INTEGER DEFAULT 0,
                    is_private INTEGER DEFAULT 0,
                    is_verified INTEGER DEFAULT 0,
                    full_name TEXT,
                    biography TEXT,
                    category TEXT,
                    profile_pic_url TEXT,
                    scraped_at TEXT
                )
                """
            )

    @property
    def name(self) -> str:
        return "sqlite-scraper"

    def available(self) -> bool:
        try:
            with _connect(self._db) as conn:
                conn.execute("SELECT 1 FROM profiles LIMIT 1").fetchone()
            return True
        except Exception:
            return False

    def status(self) -> dict:
        try:
            ok = self.available()
            return {
                "available": ok,
                "type": "sqlite",
                "path": str(self._db),
                "profiles": self.count_profiles() if ok else 0,
            }
        except Exception as exc:
            return {"available": False, "type": "sqlite", "path": str(self._db), "error": str(exc)}

    def save_profile(self, username, url, profile_info, post_info, stats=None) -> bool:
        import datetime

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

        with _connect(self._db) as conn:
            conn.execute(
                """
                INSERT INTO profiles (username, url, profile_info, post_info, followers,
                    following, media_count, is_private, is_verified, full_name, biography,
                    category, profile_pic_url, scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(username) DO UPDATE SET
                    url=excluded.url,
                    profile_info=excluded.profile_info,
                    post_info=excluded.post_info,
                    followers=excluded.followers,
                    following=excluded.following,
                    media_count=excluded.media_count,
                    is_private=excluded.is_private,
                    is_verified=excluded.is_verified,
                    full_name=excluded.full_name,
                    biography=excluded.biography,
                    category=excluded.category,
                    profile_pic_url=excluded.profile_pic_url,
                    scraped_at=excluded.scraped_at
                """,
                (
                    username.strip().lstrip("@"),
                    url,
                    json.dumps(profile_info, ensure_ascii=False),
                    json.dumps(post_info, ensure_ascii=False),
                    followers, following, media_count,
                    int(is_private), int(is_verified),
                    full_name, biography, category, profile_pic_url,
                    datetime.datetime.now().isoformat(),
                ),
            )
        return True

    def get_profile(self, username) -> dict | None:
        with _connect(self._db) as conn:
            row = conn.execute(
                "SELECT * FROM profiles WHERE username=?", (username.strip().lstrip("@"),)
            ).fetchone()
        return _row_to_profile(row) if row else None

    def search_profiles(self, query, limit=20, offset=0) -> list[dict]:
        needle = f"%{query.strip()}%"
        with _connect(self._db) as conn:
            rows = conn.execute(
                """
                SELECT * FROM profiles
                WHERE username LIKE ? OR full_name LIKE ? OR biography LIKE ? OR category LIKE ?
                ORDER BY scraped_at DESC LIMIT ? OFFSET ?
                """,
                (needle, needle, needle, needle, limit, offset),
            ).fetchall()
        return [_row_to_profile(row) for row in rows]

    def count_search(self, query: str) -> int | None:
        needle = f"%{query.strip()}%"
        with _connect(self._db) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM profiles
                WHERE username LIKE ? OR full_name LIKE ? OR biography LIKE ? OR category LIKE ?
                """,
                (needle, needle, needle, needle),
            ).fetchone()
        return int(row["c"])

    def count_profiles(self) -> int:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM profiles").fetchone()
        return int(row["c"])

    def sum_media_count(self) -> int:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT COALESCE(SUM(media_count), 0) AS total FROM profiles").fetchone()
        return int(row["total"])

    def top_profiles(self, limit: int = 10, offset: int = 0) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM profiles ORDER BY followers DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_row_to_profile(row) for row in rows]

    def list_recent(self, limit=20) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM profiles ORDER BY scraped_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_profile(row) for row in rows]

    def profile_growth(self, days: int = 14) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT day, c FROM ("
                "  SELECT substr(scraped_at, 1, 10) AS day, COUNT(*) AS c "
                "  FROM profiles WHERE scraped_at IS NOT NULL "
                "  GROUP BY day ORDER BY day DESC LIMIT ?"
                ") ORDER BY day ASC",
                (int(days),),
            ).fetchall()
        return [{"date": row["day"], "count": int(row["c"])} for row in rows]

    def list_tables(self) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables = []
            for row in rows:
                name = row["name"]
                info = conn.execute(f"PRAGMA table_info({name})").fetchall()
                count = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
                tables.append(
                    {
                        "name": name,
                        "columns": [
                            {"name": c["name"], "type": c["type"],
                             "nullable": not bool(c["notnull"]), "pk": bool(c["pk"])}
                            for c in info
                        ],
                        "rows": int(count),
                    }
                )
        return tables

    def list_views(self) -> list[dict]:
        """Read-model views over the local store (mirror of the PG views).

        v_profiles_by_followers / v_dashboard_stats are computed from this DB's
        profiles table; v_recent_activity is pulled from the metadata DB
        (creatoros.db) that also holds jobs/users/features/menus.
        """
        from app.core.config import settings as _settings

        meta_path = Path(_settings.metadata_db_path) if _settings.metadata_db_path else self._db
        views = []
        with _connect(self._db) as conn:
            top = conn.execute(
                "SELECT username, url, followers, following, media_count, is_private, "
                "is_verified, full_name, biography, category, profile_pic_url, scraped_at "
                "FROM profiles ORDER BY followers DESC LIMIT 5"
            ).fetchall()
            creators = conn.execute("SELECT COUNT(*) AS c FROM profiles").fetchone()["c"]
            media = conn.execute("SELECT COALESCE(SUM(media_count),0) AS s FROM profiles").fetchone()["s"]
        views.append(
            {
                "name": "v_profiles_by_followers",
                "columns": ["username", "followers", "media_count", "category", "scraped_at"],
                "rows": len(top),
                "sample": [dict(row) for row in top],
            }
        )
        views.append(
            {
                "name": "v_dashboard_stats",
                "columns": ["creators", "posts_analyzed", "jobs_running"],
                "rows": 1,
                "sample": [{"creators": creators, "posts_analyzed": media, "jobs_running": 0}],
            }
        )
        if meta_path.exists():
            try:
                with _connect(meta_path) as conn:
                    act = conn.execute("SELECT id, user, action, target, detail, created_at"
                                       " FROM audit_logs ORDER BY created_at DESC LIMIT 5").fetchall()
                views.append(
                    {
                        "name": "v_recent_activity",
                        "columns": ["user", "action", "target", "created_at"],
                        "rows": len(act),
                        "sample": [dict(row) for row in act],
                    }
                )
            except Exception:
                pass
        return views

    def ingest_from_keylist(self, keylist_path, on_event=None, table=None):
        raise NotImplementedError("local SQLite store has no SQL Server ingest")

    # ------------------------------------------------------------ marketplace
    def upsert_profile(self, record: dict) -> bool:
        import datetime
        username = str(record.get("username") or "").strip().lstrip("@")
        if not username:
            return False
        with _connect(self._db) as conn:
            conn.execute(
                """
                INSERT INTO profiles (username, url, profile_info, post_info, followers,
                    following, media_count, is_private, is_verified, full_name, biography,
                    category, profile_pic_url, scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(username) DO UPDATE SET
                    url=excluded.url,
                    profile_info=excluded.profile_info,
                    post_info=excluded.post_info,
                    followers=excluded.followers,
                    following=excluded.following,
                    media_count=excluded.media_count,
                    is_private=excluded.is_private,
                    is_verified=excluded.is_verified,
                    full_name=excluded.full_name,
                    biography=excluded.biography,
                    category=excluded.category,
                    profile_pic_url=excluded.profile_pic_url,
                    scraped_at=excluded.scraped_at
                """,
                (
                    username,
                    str(record.get("url") or f"https://www.instagram.com/{username}/"),
                    json.dumps({"marketplace": True}, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    int(record.get("followers") or 0),
                    int(record.get("following") or 0),
                    int(record.get("media_count") or 0),
                    int(bool(record.get("is_private"))),
                    int(bool(record.get("is_verified"))),
                    str(record.get("full_name") or ""),
                    str(record.get("biography") or ""),
                    str(record.get("category") or ""),
                    str(record.get("profile_pic_url") or ""),
                    datetime.datetime.now().isoformat(),
                ),
            )
        return True

    def count_profiles_by_category(self, category: str) -> int:
        needle = f"%{category.strip()}%"
        with _connect(self._db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM profiles WHERE category LIKE ?", (needle,)
            ).fetchone()
        return int(row["c"])

    def search_profiles_by_category(self, category: str, limit: int = 50) -> list[dict]:
        needle = f"%{category.strip()}%"
        with _connect(self._db) as conn:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE category LIKE ? ORDER BY followers DESC LIMIT ?",
                (needle, limit),
            ).fetchall()
        return [_row_to_profile(row) for row in rows]


def _row_to_profile(row: sqlite3.Row) -> dict:
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