-- CreatorOS PostgreSQL schema (applied automatically on backend boot).
-- Database: yinstagram   Schema: creatoros
-- Mirrors the SQLite stores 1:1 so any volume of jobs/projects/RBAC fits the
-- admin database. JSON columns (steps/log/result/outputs/profile_info/post_info)
-- are stored as TEXT and round-tripped by the port adapters.

-- Idempotent: safe to run on every boot (CREATE IF NOT EXISTS throughout).
CREATE SCHEMA IF NOT EXISTS creatoros;

SET search_path = creatoros;

-- ------------------------------------------------------------------ metadata
CREATE TABLE IF NOT EXISTS app_meta (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL DEFAULT ''
);

-- -------------------------------------------------------------------- jobs
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    project      TEXT,
    status       TEXT NOT NULL,
    progress     REAL NOT NULL DEFAULT 0,
    current_step TEXT NOT NULL DEFAULT '',
    steps        TEXT NOT NULL DEFAULT '[]',
    log          TEXT NOT NULL DEFAULT '[]',
    result       TEXT NOT NULL DEFAULT '{}',
    error        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs (created_at DESC);
-- migration for databases created before the payload column existed
ALTER TABLE creatoros.jobs ADD COLUMN IF NOT EXISTS payload TEXT NOT NULL DEFAULT '{}';

-- ---------------------------------------------------------------- projects
CREATE TABLE IF NOT EXISTS projects (
    name           TEXT PRIMARY KEY,
    status         TEXT NOT NULL,
    urls_pending   INTEGER NOT NULL DEFAULT 0,
    urls_done      INTEGER NOT NULL DEFAULT 0,
    creators_saved INTEGER NOT NULL DEFAULT 0,
    outputs        TEXT NOT NULL DEFAULT '[]',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_urls (
    project      TEXT NOT NULL,
    url          TEXT NOT NULL,
    state        TEXT NOT NULL,           -- pending | done
    processed_at TEXT,
    PRIMARY KEY (project, url)
);

CREATE INDEX IF NOT EXISTS idx_project_urls_state ON project_urls (project, state);

-- ------------------------------------------------------------------- users
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL DEFAULT '',
    username      TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'admin',
    status        TEXT NOT NULL DEFAULT 'active',
    password_hash TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    last_login    TEXT
);
-- migration for databases created before the username column existed
ALTER TABLE creatoros.users ADD COLUMN IF NOT EXISTS username TEXT NOT NULL DEFAULT '';

-- ----------------------------------------------------------------- features
CREATE TABLE IF NOT EXISTS features (
    key        TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    group_name TEXT NOT NULL DEFAULT 'General',
    roles      TEXT NOT NULL DEFAULT 'admin,user'
);
-- migration for databases created before the roles column existed
ALTER TABLE creatoros.features ADD COLUMN IF NOT EXISTS roles TEXT NOT NULL DEFAULT 'admin,user';

-- --------------------------------------------------------------- menus
CREATE TABLE IF NOT EXISTS menus (
    key        TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    path       TEXT NOT NULL,
    group_name TEXT NOT NULL,
    icon       TEXT NOT NULL DEFAULT '',
    "position" INTEGER NOT NULL DEFAULT 0,
    feature    TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------------------------- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id         TEXT PRIMARY KEY,
    "user"     TEXT NOT NULL,
    action     TEXT NOT NULL,
    target     TEXT NOT NULL DEFAULT '',
    detail     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at DESC);

-- ------------------------------------------------------- connection_logs
CREATE TABLE IF NOT EXISTS connection_logs (
    id         TEXT PRIMARY KEY,
    "user"     TEXT NOT NULL,
    event      TEXT NOT NULL,               -- signup | login | logout
    ip         TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    device     TEXT NOT NULL DEFAULT '',
    browser    TEXT NOT NULL DEFAULT '',
    os         TEXT NOT NULL DEFAULT '',
    location   TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_connections_created ON connection_logs (created_at DESC);

-- ------------------------------------------------------------ api_traffic
CREATE TABLE IF NOT EXISTS api_traffic (
    id          TEXT PRIMARY KEY,
    "user"      TEXT NOT NULL,
    email       TEXT NOT NULL DEFAULT '',
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    ip          TEXT NOT NULL DEFAULT '',
    user_agent  TEXT NOT NULL DEFAULT '',
    device      TEXT NOT NULL DEFAULT '',
    browser     TEXT NOT NULL DEFAULT '',
    os          TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traffic_created ON api_traffic (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traffic_path ON api_traffic (path);
CREATE INDEX IF NOT EXISTS idx_traffic_status ON api_traffic (status_code);

-- -------------------------------------------------------------- campaigns
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
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status);
CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns (created_at DESC);

-- -------------------------------------------------------------- budget ledger
CREATE TABLE IF NOT EXISTS campaign_budgets (
    id             TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL,
    amount         INTEGER NOT NULL DEFAULT 0,
    currency       TEXT NOT NULL DEFAULT 'USD',
    category       TEXT NOT NULL DEFAULT 'creator',
    status         TEXT NOT NULL DEFAULT 'planned',
    creator_username TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_events (
    id             TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL,
    budget_id      TEXT NOT NULL,
    amount         INTEGER NOT NULL DEFAULT 0,
    currency       TEXT NOT NULL DEFAULT 'USD',
    category       TEXT NOT NULL DEFAULT 'creator',
    status         TEXT NOT NULL DEFAULT 'planned',
    creator_username TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_campaign_budgets_campaign ON campaign_budgets (campaign_id);
CREATE INDEX IF NOT EXISTS idx_budget_events_campaign ON budget_events (campaign_id);

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
);

CREATE INDEX IF NOT EXISTS idx_campaign_creators_campaign ON campaign_creators (campaign_id, rank);

CREATE TABLE IF NOT EXISTS campaign_requests (
    id               TEXT PRIMARY KEY,
    campaign_id      TEXT NOT NULL,
    creator_username TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    message          TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_campaign_requests_campaign ON campaign_requests (campaign_id);

-- --------------------------------------------------------------- profiles
CREATE TABLE IF NOT EXISTS profiles (
    username        TEXT PRIMARY KEY,
    url             TEXT,
    profile_info    TEXT,
    post_info       TEXT,
    followers       INTEGER DEFAULT 0,
    following       INTEGER DEFAULT 0,
    media_count     INTEGER DEFAULT 0,
    is_private      BOOLEAN DEFAULT FALSE,
    is_verified     BOOLEAN DEFAULT FALSE,
    full_name       TEXT,
    biography       TEXT,
    category        TEXT,
    profile_pic_url TEXT,
    scraped_at      TEXT,
    -- collaboration availability
    availability_status TEXT DEFAULT 'unknown',
    available_from      TEXT,
    available_until     TEXT,
    collaboration_types TEXT,
    preferred_categories TEXT DEFAULT '',
    minimum_budget      INTEGER DEFAULT 0,
    data_freshness      TEXT DEFAULT 'never collected',
    -- data lineage
    source TEXT DEFAULT 'unknown',
    collected_by TEXT,
    collection_job TEXT,
    collected_at TIMESTAMP,
    freshness TEXT DEFAULT 'never collected'
);

CREATE INDEX IF NOT EXISTS idx_profiles_followers ON profiles (followers DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_scraped ON profiles (scraped_at DESC);

-- ------------------------------------------------- Step 2: creator workspace
-- favorites / saved creators (marketplace "save" marks a profile, favorite is explicit)
CREATE TABLE IF NOT EXISTS creator_favorites (
    username   TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL,
    PRIMARY KEY (username, created_by)
);

-- named creator lists + many-to-many members
CREATE TABLE IF NOT EXISTS creator_lists (
    name       TEXT PRIMARY KEY,
    created_by TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS creator_list_members (
    list_name TEXT NOT NULL,
    username  TEXT NOT NULL,
    added_at  TEXT NOT NULL,
    PRIMARY KEY (list_name, username)
);

CREATE INDEX IF NOT EXISTS idx_creator_list_members_user ON creator_list_members (username);

-- custom fields on creators, campaigns, media, outreach, tasks, lists
CREATE TABLE IF NOT EXISTS custom_fields (
    id          TEXT PRIMARY KEY,
    key         TEXT NOT NULL,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,  -- text, long_text, number, decimal, boolean, date, datetime, url, select, multi_select, tag, user, currency
    domain      TEXT NOT NULL DEFAULT 'creator',  -- creator, campaign, media, outreach, task, list
    is_required   BOOLEAN NOT NULL DEFAULT FALSE,
    is_visible   BOOLEAN NOT NULL DEFAULT TRUE,
    role_access  TEXT NOT NULL DEFAULT 'all',  -- all, admin, user
    default_value TEXT,
    options      TEXT,  -- JSON for select/multi_select
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_field_values (
    id          TEXT PRIMARY KEY,
    domain_id   TEXT NOT NULL,  -- the id of the creator/campaign/media/etc.
    field_key   TEXT NOT NULL,
    value       TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_custom_field_values_domain ON custom_field_values (domain_id, field_key);
CREATE INDEX IF NOT EXISTS idx_custom_field_values_field ON custom_field_values (field_key);

-- data lineage tracking
CREATE TABLE IF NOT EXISTS data_lineage (
    id          TEXT PRIMARY KEY,
    object_type TEXT NOT NULL,  -- creator, media, campaign, deliverable, etc.
    object_id   TEXT NOT NULL,
    source      TEXT NOT NULL,  -- instagram, csv, manual, api, demo
    collected_by TEXT,
    session_id  TEXT,
    collected_at TIMESTAMP,
    updated_at  TIMESTAMP,
    fresness    TEXT DEFAULT 'never collected',  -- fresh, stale, expired, never collected
    calculated  TEXT,
    estimated   TEXT,
    ai_generated BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_data_lineage_object ON data_lineage (object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_data_lineage_source ON data_lineage (source);

-- tags on creators (canonical tag strings)
CREATE TABLE IF NOT EXISTS creator_tags (
    username   TEXT NOT NULL,
    tag        TEXT NOT NULL,
    PRIMARY KEY (username, tag)
);

-- notes attached to a creator
CREATE TABLE IF NOT EXISTS creator_notes (
    id         TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT 'admin',
    note       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_creator_notes_username ON creator_notes (username, created_at DESC);

-- deliverables attached to a campaign creator
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
);

CREATE INDEX IF NOT EXISTS idx_campaign_deliverables_campaign ON campaign_deliverables (campaign_id, creator_username);
CREATE INDEX IF NOT EXISTS idx_campaign_deliverables_status ON campaign_deliverables (status);

-- historical per-creator metric snapshots (never overwritten)
CREATE TABLE IF NOT EXISTS creator_snapshots (
    id          TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    followers   INTEGER NOT NULL DEFAULT 0,
    following   INTEGER NOT NULL DEFAULT 0,
    media_count INTEGER NOT NULL DEFAULT 0,
    avg_likes   INTEGER NOT NULL DEFAULT 0,
    avg_comments INTEGER NOT NULL DEFAULT 0,
    engagement_percent FLOAT NOT NULL DEFAULT 0,
    collected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_creator_snapshots_user ON creator_snapshots (username, collected_at DESC);

-- media collected per creator (unique by media_id; no duplicate rows)
CREATE TABLE IF NOT EXISTS media (
    media_id      TEXT PRIMARY KEY,
    shortcode     TEXT NOT NULL DEFAULT '',
    username      TEXT NOT NULL,
    media_type    TEXT NOT NULL DEFAULT 'photo',
    caption       TEXT NOT NULL DEFAULT '',
    taken_at      TEXT,
    likes         INTEGER NOT NULL DEFAULT 0,
    comments      INTEGER NOT NULL DEFAULT 0,
    views         INTEGER NOT NULL DEFAULT 0,
    thumbnail_url TEXT NOT NULL DEFAULT '',
    video_url     TEXT NOT NULL DEFAULT '',
    location      TEXT NOT NULL DEFAULT '',
    download_status TEXT NOT NULL DEFAULT 'none',
    collected_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_username ON media (username, taken_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_type ON media (media_type);

-- import history (running list of ingestion operations)
CREATE TABLE IF NOT EXISTS imports (
    id         TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    count      INTEGER NOT NULL DEFAULT 0,
    detail     TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL
);

-- discovery search history
CREATE TABLE IF NOT EXISTS search_history (
    id         TEXT PRIMARY KEY,
    "user"     TEXT NOT NULL,
    query      TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'creator',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history (created_at DESC);