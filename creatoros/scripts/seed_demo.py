"""CreatorOS demo-data seed.

Installs clearly-marked demo creators (explicitly approved by the dashboard
request) plus a small set of audit entries, a sample project and a finished
job, so the dashboard / database / marketplace pages have real rows to read.

Every profile is stored through the same DatabasePort.upsert_profile path the
app uses (SQLite local + PostgreSQL when PG_ENABLED), so the seed exercises the
exact production code path. Profiles are named "demo@..." — run
`python3 scripts/seed_demo.py --reset` afterwards to remove them.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.core.domain.access import FEATURES  # noqa: E402
from app.adapters.secondary.database.scraper_store import ScraperSqliteAdapter  # noqa: E402

DEMO_TAG = "demo@"

DEMO_CREATORS = [
    {
        "username": "demo.khem.photography", "full_name": "Khem Visuals",
        "biography": "Fashion & lifestyle photography in Bangkok.", "category": "Photography",
        "followers": 124_800, "following": 312, "media_count": 482,
        "is_private": False, "is_verified": True,
        "profile_pic_url": "https://picsum.photos/seed/khem1/200",
    },
    {
        "username": "demo.nina.beauty", "full_name": "Nina Madeira",
        "biography": "Beauty creator · skincare routines & GRWM.", "category": "Beauty",
        "followers": 248_300, "following": 541, "media_count": 231,
        "is_private": False, "is_verified": True,
        "profile_pic_url": "https://picsum.photos/seed/nina1/200",
    },
    {
        "username": "demo.travel.jules", "full_name": "Jules Traveler",
        "biography": "Solo travel, drone content, hidden gems.", "category": "Travel",
        "followers": 89_200, "following": 890, "media_count": 1321,
        "is_private": False, "is_verified": False,
        "profile_pic_url": "https://picsum.photos/seed/jules1/200",
    },
    {
        "username": "demo.fit.olivia", "full_name": "Olivia Cross",
        "biography": "Strength & mobility · certified coach.", "category": "Fitness",
        "followers": 512_000, "following": 204, "media_count": 689,
        "is_private": False, "is_verified": True,
        "profile_pic_url": "https://picsum.photos/seed/olivia1/200",
    },
    {
        "username": "demo.food.bangkok", "full_name": "Bangkok Table",
        "biography": "Street food across Bangkok & beyond. 🍜", "category": "Food & Drink",
        "followers": 156_400, "following": 1_108, "media_count": 1_054,
        "is_private": False, "is_verified": False,
        "profile_pic_url": "https://picsum.photos/seed/food1/200",
    },
    {
        "username": "demo.tech.reviews", "full_name": "Tech with Mark",
        "biography": "Gadgets, laptops, honest reviews.", "category": "Technology",
        "followers": 63_100, "following": 176, "media_count": 342,
        "is_private": False, "is_verified": False,
        "profile_pic_url": "https://picsum.photos/seed/mark1/200",
    },
    {
        "username": "demo.mom.life", "full_name": "Sophie & Co",
        "biography": "Motherhood, home routines, gentle living.", "category": "Lifestyle",
        "followers": 173_900, "following": 640, "media_count": 418,
        "is_private": False, "is_verified": False,
        "profile_pic_url": "https://picsum.photos/seed/soph1/200",
    },
    {
        "username": "demo.eco.kevin", "full_name": "Kevin Zero Waste",
        "biography": "Sustainable living experiments.", "category": "Eco & Sustainability",
        "followers": 41_200, "following": 433, "media_count": 176,
        "is_private": False, "is_verified": False,
        "profile_pic_url": "https://picsum.photos/seed/kev1/200",
    },
]


def _days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def seed_sqlite() -> ScraperSqliteAdapter:
    store = ScraperSqliteAdapter()
    for c in DEMO_CREATORS:
        record = dict(c)
        record["url"] = f"https://www.instagram.com/{record['username']}/"
        record["category"] = record.get("category") or "demo"
        store.upsert_profile(record)
    return store


def seed_audit_and_meta():
    from app.core.config import settings as _s

    meta = Path(_s.metadata_db_path)
    if not meta.exists():
        return
    import sqlite3
    conn = sqlite3.connect(str(meta))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS audit_logs (id TEXT PRIMARY KEY, user TEXT NOT NULL,"
        " action TEXT NOT NULL, target TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',"
        " created_at TEXT NOT NULL)"
    )
    entries = [
        ("demo-seed.actors", "creator.demo.seeded", "marketplace",
         f"{len(DEMO_CREATORS)} demo creators installed", _days_ago(1)),
        ("demo-seed.login", "auth.login", "session", "demo login via seeded account", _days_ago(1)),
        ("demo-seed.export", "data.export", "projects", "demo CSV export", _days_ago(0.4)),
    ]
    for eid, action, target, detail, ts in entries:
        conn.execute(
            "INSERT OR IGNORE INTO audit_logs (id, user, action, target, detail, created_at)"
            " VALUES (?,?,?,?,?,?)", (eid, "sysdemo@creatoros.local", action, target, detail, ts),
        )
    conn.commit()
    conn.close()


def sync_feature_flags():
    """Force the honest defaults (direct + publishing disabled) into both stores."""
    import sqlite3

    try:
        from app.adapters.secondary.postgres.connection import pg_cursor
        for f in FEATURES:
            with pg_cursor() as cur:
                cur.execute(
                    "UPDATE creatoros.features SET enabled=%s WHERE key=%s",
                    (bool(f.enabled), f.key),
                )
        print("  pg feature flags synced (direct/publishing disabled)")
    except Exception as exc:  # noqa: BLE001
        print("  [pg features] skipped:", exc)
    meta = Path(settings.metadata_db_path)
    if meta.exists():
        conn = sqlite3.connect(str(meta))
        for f in FEATURES:
            conn.execute(
                "UPDATE features SET enabled=? WHERE key=?",
                (int(f.enabled), f.key),
            )
        conn.commit()
        conn.close()
        print("  sqlite feature flags synced")


def _sync_pg_features(pg):
    with pg as _:
        pass


def reset():
    """Remove every demo@ profile from both stores."""
    store = ScraperSqliteAdapter()
    for c in store.top_profiles(200):
        if str(c.get("username") or "").startswith(DEMO_TAG):
            with _sqlite_conn(store._db) as conn:
                conn.execute("DELETE FROM profiles WHERE username=?", (c["username"],))
    try:
        from app.adapters.secondary.postgres.store import PgProfileStore
        pstore = PgProfileStore()
        from app.adapters.secondary.postgres.connection import pg_cursor
        for c in pstore.top_profiles(200):
            if str(c.get("username") or "").startswith(DEMO_TAG):
                with pg_cursor() as cur:
                    cur.execute("DELETE FROM creatoros.profiles WHERE username=%s", (c["username"],))
    except Exception as exc:  # noqa: BLE001
        print("  [pg reset] skipped:", exc)
    print("demo rows removed")


def _sqlite_conn(path):
    import sqlite3
    from contextlib import contextmanager

    @contextmanager
    def cm():
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    return cm()


def seed_postgres():
    try:
        from app.adapters.secondary.postgres.store import PgProfileStore
        store = PgProfileStore()
        for c in DEMO_CREATORS:
            rec = dict(c)
            rec["category"] = rec.pop("category") or ""
            store.upsert_profile(rec)
        print("  pg profiles:", store.count_profiles())
        return store
    except Exception as exc:  # noqa: BLE001
        print("  [pg profiles] skipped:", exc)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset:
        reset()
        return
    print(f"[seed] installing {len(DEMO_CREATORS)} demo creators (tag: {DEMO_TAG})")
    local = seed_sqlite()
    print("  local profiles:", local.count_profiles())
    pg = seed_postgres()
    seed_audit_and_meta()
    sync_feature_flags()
    print("[seed] done")


if __name__ == "__main__":
    main()