"""SQLite adapter for campaigns (fallback store when Postgres is unavailable)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.core.domain.campaign import Campaign, CampaignCreator, CampaignRequest
from app.core.ports.campaign import CampaignStorePort

_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        id             TEXT PRIMARY KEY,
        name           TEXT NOT NULL,
        budget_min     INTEGER NOT NULL DEFAULT 0,
        budget_max     INTEGER NOT NULL DEFAULT 0,
        target_count   INTEGER NOT NULL DEFAULT 10,
        location       TEXT NOT NULL DEFAULT '',
        audience       TEXT NOT NULL DEFAULT '',
        min_engagement FLOAT NOT NULL DEFAULT 0,
        status         TEXT NOT NULL DEFAULT 'draft',
        notes          TEXT NOT NULL DEFAULT '',
        created_at     TEXT NOT NULL,
        updated_at     TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status)"
    """
    CREATE TABLE IF NOT EXISTS campaign_creators (
        id               TEXT PRIMARY KEY,
        campaign_id      TEXT NOT NULL,
        creator_username TEXT NOT NULL,
        score            FLOAT NOT NULL DEFAULT 0,
        match_pct        FLOAT NOT NULL DEFAULT 0,
        rank             INTEGER NOT NULL DEFAULT 0,
        status           TEXT NOT NULL DEFAULT 'matched',
        followers        INTEGER NOT NULL DEFAULT 0,
        full_name        TEXT NOT NULL DEFAULT '',
        category         TEXT NOT NULL DEFAULT '',
        location         TEXT NOT NULL DEFAULT '',
        biography        TEXT NOT NULL DEFAULT '',
        engagement       FLOAT NOT NULL DEFAULT 0,
        created_at       TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_campaign_creators_campaign ON campaign_creators (campaign_id, rank)"
    """
    CREATE TABLE IF NOT EXISTS campaign_requests (
        id               TEXT PRIMARY KEY,
        campaign_id      TEXT NOT NULL,
        creator_username TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'pending',
        message          TEXT NOT NULL DEFAULT '',
        created_at       TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_campaign_requests_campaign ON campaign_requests (campaign_id)"
    """
    CREATE TABLE IF NOT EXISTS campaign_deliverables (
        id             TEXT PRIMARY KEY,
        campaign_id    TEXT NOT NULL,
        creator_username TEXT NOT NULL,
        deliverable_type TEXT NOT NULL,
        quantity       INTEGER NOT NULL DEFAULT 1,
        deadline       TEXT,
        submitted_at   TEXT,
        approved_at    TEXT,
        published_at   TEXT,
        url            TEXT,
        status         TEXT NOT NULL DEFAULT 'not_started',
        notes          TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_campaign_deliverables_campaign ON campaign_deliverables (campaign_id, creator_username)",
    "CREATE INDEX IF NOT EXISTS idx_campaign_deliverables_status ON campaign_deliverables (status)"
    """
    CREATE TABLE IF NOT EXISTS custom_fields (
        id          TEXT PRIMARY KEY,
        key         TEXT NOT NULL,
        name        TEXT NOT NULL,
        type        TEXT NOT NULL,
        domain      TEXT NOT NULL DEFAULT 'creator',
        is_required   BOOLEAN NOT NULL DEFAULT FALSE,
        is_visible   BOOLEAN NOT NULL DEFAULT TRUE,
        role_access  TEXT NOT NULL DEFAULT 'all',
        default_value TEXT,
        options      TEXT,
        created_at   TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_custom_field_values_domain ON custom_field_values (domain_id, field_key)"
    """
    CREATE TABLE IF NOT EXISTS custom_field_values (
        id          TEXT PRIMARY KEY,
        domain_id   TEXT NOT NULL,
        field_key   TEXT NOT NULL,
        value       TEXT NOT NULL,
        created_at  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_custom_field_values_field ON custom_field_values (field_key)",
    
    """
    CREATE TABLE IF NOT EXISTS data_lineage (
        id          TEXT PRIMARY KEY,
        object_type TEXT NOT NULL,
        object_id   TEXT NOT NULL,
        source      TEXT NOT NULL,
        collected_by TEXT,
        session_id  TEXT,
        collected_at TIMESTAMP,
        updated_at  TIMESTAMP,
        fresness    TEXT DEFAULT 'never collected',
        calculated  TEXT,
        estimated   TEXT,
        ai_generated BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_data_lineage_object ON data_lineage (object_type, object_id)
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_data_lineage_source ON data_lineage (source)
    """

]

def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


class SqliteCampaignStore(CampaignStorePort):
    """Driven adapter: campaigns + creator matching + deliverables + requests + custom fields persisted in SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        self._db = Path(db_path or "data/creatoros.db")
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db) as conn:
            for schema in _SCHEMA:
                conn.execute(schema)

    # ------------------------------------------------------ CRUD
    def create_campaign(self, campaign: Campaign) -> Campaign:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO campaigns (id, name, budget_min, budget_max, target_count, location, audience, min_engagement, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (campaign.id, campaign.name, campaign.budget_min, campaign.budget_max, campaign.target_count,
                 campaign.location, campaign.audience, campaign.min_engagement, campaign.status, campaign.notes,
                 campaign.created_at, campaign.updated_at),
            )
        return campaign

    def update_campaign(self, campaign: Campaign) -> Campaign:
        with _connect(self._db) as conn:
            conn.execute(
                "UPDATE campaigns SET name=?, budget_min=?, budget_max=?, target_count=?, location=?, audience=?, min_engagement=?, status=?, notes=?, updated_at=? WHERE id=?",
                (campaign.name, campaign.budget_min, campaign.budget_max, campaign.target_count,
                 campaign.location, campaign.audience, campaign.min_engagement, campaign.status, campaign.notes,
                 campaign.updated_at, campaign.id),
            )
        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with _connect(self._db) as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        return self._row_to_campaign(row) if row else None

    def list_campaigns(self) -> list[Campaign]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
        return [self._row_to_campaign(r) for r in rows]

    def delete_campaign(self, campaign_id: str) -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
            conn.execute("DELETE FROM campaign_creators WHERE campaign_id=?", (campaign_id,))
            conn.execute("DELETE FROM campaign_requests WHERE campaign_id=?", (campaign_id,))
            conn.execute("DELETE FROM campaign_deliverables WHERE campaign_id=?", (campaign_id,))
            conn.execute("DELETE FROM custom_fields WHERE id IN (SELECT domain_id FROM custom_field_values WHERE domain_id LIKE ?)", (f"%{campaign_id}%",))
            conn.execute("DELETE FROM custom_field_values WHERE domain_id LIKE ?", (f"%{campaign_id}%",))
        return cur.rowcount > 0

    # ------------------------------------------------------ campaign creators
    def replace_creators(self, campaign_id: str, rows: list[CampaignCreator]) -> None:
        with _connect(self._db) as conn:
            conn.execute("DELETE FROM campaign_creators WHERE campaign_id=?", (campaign_id,))
            conn.executemany(
                "INSERT INTO campaign_creators (id, campaign_id, creator_username, score, match_pct, rank, status, followers, full_name, category, location, biography, engagement, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(r.id, r.campaign_id, r.creator_username, r.score, r.match_pct, r.rank, r.status,
                  r.followers, r.full_name, r.category, r.location, r.biography, r.engagement, r.created_at)
                 for r in rows],
            )

    def list_creators(self, campaign_id: str) -> list[CampaignCreator]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM campaign_creators WHERE campaign_id=? ORDER BY rank", (campaign_id,)).fetchall()
        return [self._row_to_campaign_creator(r) for r in rows]

    def set_creator_status(self, campaign_id: str, username: str, status: str) -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute("UPDATE campaign_creators SET status=? WHERE campaign_id=? AND creator_username=?", (status, campaign_id, username))
        return cur.rowcount > 0

    # ------------------------------------------------------ campaign requests
    def list_requests(self, campaign_id: str) -> list[CampaignRequest]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM campaign_requests WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,)).fetchall()
        return [self._row_to_request(r) for r in rows]

    def add_request(self, request: CampaignRequest) -> CampaignRequest:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO campaign_requests (id, campaign_id, creator_username, status, message, created_at) VALUES (?,?,?,?,?,?)",
                (request.id, request.campaign_id, request.creator_username,
                 request.status, request.message, request.created_at),
            )
        return request

    def set_request_status(self, campaign_id: str, username: str, status: str) -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute("UPDATE campaign_requests SET status=? WHERE campaign_id=? AND creator_username=?", (status, campaign_id, username))
        return cur.rowcount > 0

    # ------------------------------------------------------ deliverables
    def add_deliverable(self, deliverable: dict) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO campaign_deliverables (id, campaign_id, creator_username, deliverable_type, quantity, deadline, submitted_at, approved_at, published_at, url, status, notes, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (deliverable.get("id"), deliverable.get("campaign_id"), deliverable.get("creator_username"),
                 deliverable.get("deliverable_type"), deliverable.get("quantity"), deliverable.get("deadline"),
                 deliverable.get("submitted_at"), deliverable.get("approved_at"), deliverable.get("published_at"),
                 deliverable.get("url"), deliverable.get("status"), deliverable.get("notes"), deliverable.get("created_at")),
            )
        return deliverable

    def update_deliverable_status(self, campaign_id: str, creator_username: str, status: str, notes: str = "") -> bool:
        with _connect(self._db) as conn:
            cur = conn.execute(
                "UPDATE campaign_deliverables SET status=?, notes=? WHERE campaign_id=? AND creator_username=?",
                (status, notes, campaign_id, creator_username),
            )
        return cur.rowcount > 0

    def list_deliverables(self, campaign_id: str) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM campaign_deliverables WHERE campaign_id=? ORDER BY created_at", (campaign_id,)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------ custom fields
    def upsert_custom_field(self, field: dict) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO custom_fields (id, key, name, type, domain, is_required, is_visible, role_access, default_value, options, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (key, domain) DO UPDATE SET name=?, is_required=?, is_visible=?, role_access=?, default_value=?, options=?",
                (field.get("id"), field.get("key"), field.get("name"), field.get("type"), field.get("domain"),
                 field.get("is_required"), field.get("is_visible"), field.get("role_access"),
                 field.get("default_value"), field.get("options"), field.get("created_at"),
                 field.get("name"), field.get("is_required"), field.get("is_visible"),
                 field.get("role_access"), field.get("default_value"), field.get("options")),
            )
        return field

    def get_custom_fields(self, domain: str = "creator") -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM custom_fields WHERE domain=? ORDER BY key", (domain,)).fetchall()
        return [dict(r) for r in rows]

    def set_custom_field_value(self, value: dict) -> dict:
        with _connect(self._db) as conn:
            conn.execute(
                "INSERT INTO custom_field_values (id, domain_id, field_key, value, created_at) VALUES (?,?,?,?,?) ON CONFLICT (domain_id, field_key) DO UPDATE SET value=?, created_at=?",
                (value.get("id"), value.get("domain_id"), value.get("field_key"), value.get("value"),
                 value.get("created_at"),
                 value.get("value"), value.get("created_at")),
            )
        return value

    def get_custom_field_values(self, domain_id: str, field_key: str) -> list[dict]:
        with _connect(self._db) as conn:
            rows = conn.execute("SELECT * FROM custom_field_values WHERE domain_id=? AND field_key=?", (domain_id, field_key)).fetchall()
        return [dict(r) for r in rows]


# Create the store instance
campaign_store = SqliteCampaignStore()
