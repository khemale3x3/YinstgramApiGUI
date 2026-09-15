# KreatOS — Database Schema

App store = PostgreSQL `creatoros` schema (primary) with a SQLite mirror (`data/creatoros.db`)
used as a graceful fallback when PG is unreachable. Scraped profiles live in
`creatoros.profiles` *and* the SQLite scraper store (`data/scraper_data.db`) — the two
paths converge on `DatabasePort.upsert_profile` so the data is identical.

DDL sources (applied automatically on boot, in order):
`data/postgres/schema.sql` → `functions.sql` → `procedures.sql` → `views.sql`.

## Tables (PostgreSQL `creatoros` schema)

| Table | Purpose | Key columns | PK | FKs |
| ----- | ------- | ----------- | -- | --- |
| `users` | App accounts | id, email, name, role, status, password_hash, created_at, last_login | id | — |
| `features` | Feature flags | key, label, enabled, group_name, roles | key | — |
| `menus` | Dynamic sidebar map | key, label, path, group_name, icon, position, feature | key | — |
| `audit_logs` | Audit trail | id, user, action, target, detail, created_at | id | — |
| `api_traffic` | HTTP call log | id, user, email, method, path, status_code, duration_ms, ip, user_agent, ... | id | — |
| `connection_logs` | Auth/session events | id, user, event, ip, user_agent, device, browser, os, location | id | — |
| `profiles` | Creator profiles (scraped + marketplace) | username, url, profile_info, post_info, followers, following, media_count, is_private, is_verified, full_name, biography, category, profile_pic_url, scraped_at | username | — |
| `jobs` | Background jobs | id, kind, project, status, progress, current_step, steps, log, result, error, payload, created_at, updated_at | id | project → projects |
| `projects` | Run projects | name, status, urls_pending, urls_done, creators_saved, outputs, created_at, updated_at | name | — |
| `project_urls` | URL queues per project | project, url, state, processed_at | (project,url) | project → projects |
| `campaigns` | Campaigns | id, name, status, ... | id | — |
| `campaign_creators` | Campaign ↔ creator | campaign_id, username, status | (campaign_id, username) | campaign → campaigns |
| `campaign_requests` | Campaign outreach requests | id, campaign_id, username, ... | id | campaign → campaigns |
| `app_meta` | Boot/runtime metadata | key, value | key | — |

Notes:
- `jobs.status` ∈ pending, running, succeeded, failed, cancelled. `jobs.payload` stores the
  original create-request so failed/cancelled jobs can be retried (POST `/api/jobs/{id}/retry`).
- `profiles` has helpers `creatoros.upsert_profile(...)`, `count_profiles()`,
  `sum_media_count()`, `top_profiles(...)`, `search_profiles(...)` (see `functions.sql` +
  `procedures.sql`). Search predicate: username / full_name / biography / category ILIKE.
- Sensitive credentials (PG password, JWT secret, admin password) are **not** stored in these
  tables; they live in `backend/.env` only.

## Views (PostgreSQL)

| View | Reads | Columns | Purpose |
| ---- | ----- | ------- | ------- |
| `v_dashboard_stats` | profiles, jobs | creators, posts_analyzed, jobs_running | one-number dashboard chips |
| `v_jobs_by_status` | jobs | status, cnt | dashboard/Jobs legend |
| `v_recent_activity` | audit_logs | id, user, action, target, detail, created_at | recent-activity feed |
| `v_profiles_by_followers` | profiles | username…scraped_at | ranked creator list |
| `v_profiles_by_category` | profiles | category, creators, avg_followers | marketplace funnel |
| `v_engagement_insights` | profiles | username, followers, following, media_count, content_per_1k_followers | engagement proxy (media / 1k followers) |

The **Local SQLite store** mirrors these as computed read-models
(`ScraperSqliteAdapter.list_views`: `v_profiles_by_followers`, `v_dashboard_stats` over
scraper_data.db, `v_recent_activity` over creatoros.db) so the `/database` inspector works
on both backends.

## Table → View → Service connections

```text
profiles ──► v_profiles_by_followers ─► DashboardService.top_creators
profiles ──► v_profiles_by_category  ─► MarketplaceService.list_creators (counts)
profiles ──► v_engagement_insights   ─► (analytics read-model)
jobs ──────► v_jobs_by_status        ─► DashboardService.jobs stats
audit_logs ─► v_recent_activity       ─► DashboardService.recent_activity
profiles ──► profile_growth (daily)  ─► DashboardService.growth (Creator Growth chart)
```

## Demos / seed

`python3 scripts/seed_demo.py` installs 8 clearly-tagged `demo.@` creators into **both**
stores (tag `demo@`, also flagged in audits) and forces the honest feature defaults
(direct/publishing disabled). `python3 scripts/seed_demo.py --reset` removes all demo rows.

## Inspectors

- `GET /api/database/tables` — PG/SQLite table + column + row introspection.
- `GET /api/database/views` — view name, columns, row counts, sample rows.
- `GET /api/database/status` — local + remote status.