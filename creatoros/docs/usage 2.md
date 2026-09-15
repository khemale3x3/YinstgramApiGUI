# KreatOS — Usage Guide (Phase 3)

## Prerequisites

- Python 3.10+
- Node.js 18+ (frontend)
- PostgreSQL 14+ running on `localhost:5432` (default app store; pgAdmin
  recommended) — schema is auto-provisioned on first boot
- Internet access (Instagram lookups + S3 require outbound requests)
- Optional: ODBC Driver 17 for SQL Server (remote ingest), boto3 creds for S3

## 1. Start the backend

```bash
cd creatoros/backend
./run.sh
```

`run.sh` creates a virtual environment if needed, installs `requirements.txt`,
and starts the API with hot reload. (Manual alternative: `source .venv/bin/activate`
then `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.)

On boot the backend connects to PostgreSQL (`PG_*`, default
`khem@localhost:5432/yinstagram`) and applies `data/postgres/*.sql`
(schema, functions, procedures, views) idempotently — everything is created
automatically. If Postgres is unreachable the API logs a warning and falls back
to the SQLite stores, so it still boots on a bare machine.

Expected: `INFO: Uvicorn running on http://127.0.0.1:8000`

| Check | URL | Expected |
| ----- | --- | -------- |
| API root | http://127.0.0.1:8000/ | `{"application":"CreatorOS API",...}` |
| Health | http://127.0.0.1:8000/health | `{"status":"healthy",...}` |
| Interactive docs | http://127.0.0.1:8000/docs | Swagger UI |
| OpenAPI spec | http://127.0.0.1:8000/openapi.json | JSON schema |

## 2. Start the frontend

```bash
cd creatoros/frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000 — every page is behind the login guard
(default admin `khemale05@gmail.com` / `Khem101$`; override via `.env`). The
token is kept in `localStorage` and sent as `Authorization: Bearer …`.
New users can self-register from the sign-in screen (role `user`); the
full administration/system modules stay admin-only.

| URL | Page |
| --- | ---- |
| http://localhost:3000/ | Home — admin control center OR role-branch user workspace |
| http://localhost:3000/admin | Administration — feature toggles, users, audit log (admin) |
| http://localhost:3000/tracking | Tracking — API traffic + connection trail (admin) |
| http://localhost:3000/creators | Creators — analysis + CSV export |
| http://localhost:3000/accounts | Accounts — session manager |
| http://localhost:3000/settings | Settings — backend `.env` (API/SQL/S3/scraper) |
| http://localhost:3000/projects | Projects — create, URLs, run jobs |
| http://localhost:3000/jobs | Jobs — run + live-monitor scrape/analyze/export/full/index/ingest/s3_upload |
| http://localhost:3000/sessions | Sessions — active/backup accounts, import env sessions |
| http://localhost:3000/monitoring | Monitoring — jobs + session health overview |
| http://localhost:3000/data | Import / Export — CSV import + export jobs |
| http://localhost:3000/database | Database — local PostgreSQL + remote SQL Server status/search |
| http://localhost:3000/storage | Storage — S3 status, list keys, upload/download |
| http://localhost:3000/{discovery,content,hashtags,locations,analytics,collections,notes,engagement,direct,publishing} | Module pages — tabbed placeholder views driven by the menu map |
| http://localhost:3000/discovery | Discovery — unified search of the saved creator store (username/category/audience) |
| http://localhost:3000/marketplace | Marketplace — find / all / saved creators, lists, creator analysis |
| http://localhost:3000/campaigns | Campaigns — brief list + create |
| http://localhost:3000/campaigns/{id} | Campaign detail — brief editor, matched creators, outreach requests |
| http://localhost:3000/campaigns/{id}/matching | Matching — run + rank creators against the brief |
| http://localhost:3000/creators/{username} | Creator profile — the main object: Overview / Posts / Reels / Stories / Analytics / Audience / Campaigns / History |

The sidebar is dynamic: it renders the **root menu items** returned by
`GET /api/auth/me`, grouped and filtered by enabled feature flags **and** the
caller's role (`roles` column). Each module page renders its `feature:<sub>`
menu rows as in-page tabs. Toggle a feature in
**Administration → Feature Controls** to hide its menu and hard-block its API
(`403`) in one action.

The frontend calls the API at `http://127.0.0.1:8000` (`frontend/.env.local`,
`NEXT_PUBLIC_API_URL`). CORS is enabled for `http://localhost:3000`.

## 3. Typical admin workflow

1. **Administration** — confirm the feature flags for the modules you use are
   ON (Dashboard, Creators, Sessions, …). Disabled modules are hidden from the
   sidebar and rejected with `403` server-side.
2. **Settings** — set SQL Server fields (`db_server`, `db_user`, `db_password`,
   `db_table`) and S3 keys if you plan to ingest/upload; set
   `scraper_active_sessions` for how many sessions the scraper may use in parallel.
3. **Sessions** — click **Import from env** or `POST /api/sessions/env` to load
   `INSTA_SESSION_N` / `INSTA_ACCOUNT_N`; see active/backup counts.
4. **Projects** — *New Project*, paste Instagram profile URLs (or upload a CSV),
   then *Run Project*.
5. **Jobs** — pick a project and a job kind; watch status (polling every 2.5 s).
   `full` runs scrape → analyze → export in sequence; `index` covers website
   indexing; `ingest` pushes to SQL Server; `s3_upload` syncs project output to S3.
6. **Database / Storage** — verify write targets are reachable before big runs.
7. **Campaigns** — create a brief (budget, location, audience keywords, min
   engagement), then *Run matching* on its matching screen to score saved
   creators, shortlist, and queue outreach requests. Matching is v1 and works
   against whatever creators the store holds today (empty store → the UI
   explains how to collect creators).

## 4. API reference (admin routes)

Marketplace (feature-gated on `marketplace`, all require the bearer token):

- `GET /api/marketplace/categories` — `{categories: [{key, label, count}]}`
- `GET /api/marketplace/creators?category=influencers&limit=50` — saved
  profiles for a subcategory (keys: `ugc`, `influencers`, `digital`, `reel`,
  `blogger`, `generic`)
- `POST /api/marketplace/discover` `{category, limit}` — live Instagram
  search + upsert for a subcategory (returns `saved`, `skipped_private`,
  `creators`, `category_counts`); 400 with guidance when no session
- `POST /api/marketplace/save` `{username, full_name, biography, category,
  followers, following, media_count, is_private, is_verified, ...}`

All routes below require `Authorization: Bearer <token>`.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/api/auth/login` | Body `{email, password}` → `{token}` |
| `POST` | `/api/auth/signup` | Body `{email, name, password}` → `{token, role: user}` — self-registration |
| `GET` | `/api/auth/me` | Current identity: email, role, name, role-filtered features + grouped menus |
| `GET` | `/api/dashboard` | Control-center aggregates (stats incl. campaigns, top creators with score, discovery, recent activity) |
| `GET` | `/api/admin/features` | Feature flags (grouped) |
| `PUT` | `/api/admin/features/{key}` | Toggle a feature `{enabled}` — gates routes + menus immediately |
| `GET` | `/api/admin/menus` | Menu items (grouped, feature-filtered) |
| `GET` | `/api/admin/audit` | Audit log (login, feature changes, signups) |
| `GET` | `/api/admin/users` | User list (email, role, status, last login) |
| `GET` | `/api/creators/{username}` | Creator profile (public lookup) |
| `GET` | `/api/creators/{username}/posts?amount=` | Posts `1..100` |
| `GET` | `/api/campaigns` / `POST` | List campaigns / create a brief `{name, budget_min?, budget_max?, target_count?, location?, audience?, min_engagement?, notes?}` |
| `GET` / `PATCH` / `DELETE` | `/api/campaigns/{id}` | Inspect / edit / delete a campaign (detail includes creators + requests) |
| `POST` | `/api/campaigns/{id}/match` | Run creator matching against the saved profile store → ranked `campaign_creators` |
| `POST` | `/api/campaigns/{id}/request` | Queue an outreach request `{username, message?}` |
| `PATCH` | `/api/campaigns/{id}/requests/{username}` | Update request status `{status}` |
| `PATCH` | `/api/campaigns/{id}/creators/{username}` | Update creator match status `{status}` |
| `GET` / `POST` | `/api/accounts` | List / add account (login once, saves session) |
| `POST` | `/api/accounts/{username}/check` | Verify stored session |
| `DELETE` | `/api/accounts/{username}` | Remove session |
| `GET` | `/api/settings` | All settings from `backend/.env` |
| `PUT` | `/api/settings` | Write settings back to `backend/.env` |
| `GET` | `/api/sessions` | Active/backup counts + session list |
| `POST` | `/api/sessions/env` | Import `INSTA_SESSION_*` from env files (multipart upload too) |
| `GET` / `POST` | `/api/projects` | List / create projects |
| `GET` / `DELETE` | `/api/projects/{name}` | Inspect / delete project |
| `GET` / `POST` | `/api/projects/{name}/urls` | List / add profile URLs (writes `input.csv`) |
| `POST` | `/api/projects/{name}/urls/upload` | Upload URL CSV |
| `DELETE` | `/api/projects/{name}/urls/{url}` | Remove one URL |
| `POST` | `/api/projects/{name}/urls/requeue-failed` | Requeue failed URLs |
| `GET` / `POST` | `/api/jobs` | List jobs (latest first) / start a job `{kind, project?}` |
| `GET` | `/api/database` | Local SQLite + remote SQL Server status |
| `GET` | `/api/database/search?q=&limit=` | Search scraped profiles by username/name/bio/category |
| `GET` | `/api/database/top?limit=` | Highest-reach saved profiles (by followers) |
| `GET` | `/api/database/recent?limit=` | Most recently scraped profiles |
| `GET` | `/api/database/profiles/{username}` | One saved profile |
| `GET` | `/api/storage` | S3 status + keys under prefix |
| `POST` | `/api/storage/upload` | Upload a file/bytes to S3 key |
| `GET` | `/api/storage/key/{key}` | Download a key from S3 |
| `GET` | `/api/tracking/traffic?limit=` | API traffic rows (admin, feature `tracking`) |
| `GET` | `/api/tracking/connections?limit=` | Signup/login connection rows (admin, feature `tracking`) |
| `GET` | `/api/tracking/stats` | Aggregates: requests, latency, status distribution, top users (admin, feature `tracking`) |

Job kinds: `scrape`, `analyze`, `export`, `full`, `index`, `ingest`, `s3_upload`.

Example — login + start a scrape:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"khemale05@gmail.com","password":"Khem101$"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -X POST http://127.0.0.1:8000/api/jobs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"kind":"scrape","project":"my_project"}'
```

## 5. Configuration

`creatoros/backend/.env` (create from `.env.example`). This file is **read and
written by the Settings page/API**, so runtime changes persist.

| Variable | Default | Meaning |
| -------- | ------- | ------- |
| `HOST` / `PORT` | `0.0.0.0:8000` | Bind address |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `khemale05@gmail.com` / `Khem101$` | Admin login |
| `ADMIN_PASSWORD_HASH` | *(empty)* | Optional bcrypt hash; overrides password |
| `JWT_SECRET` | `change-me-in-production` | HS256 signing key |
| `JWT_EXPIRES_MINUTES` | `720` | Token lifetime |
| `SESSION_DIR` / `DATA_DIR` / `PIPELINE_DIR` | `creatoros/{sessions,data,pipeline}` | Runtime paths |
| `SCRAPER_MAX_WORKERS` / `SCRAPER_MAX_POSTS` / `SCRAPER_HEADLESS` | `8` / `40` / `true` | Scraper behavior |
| `SCRAPER_ACTIVE_SESSIONS` | `5` | Sessions usable in parallel |
| `SCRAPER_TIMEOUT` / `SCRAPER_TEST_MODE` | `30` / `false` | Scraper safety |
| `METADATA_DB_PATH` / `SCRAPER_DB_PATH` | `data/creatoros.db` / `data/scraper_data.db` | SQLite files |
| `DB_SERVER` / `DB_NAME` | *(empty)* / `CreatorsDatabase` | SQL Server host/db |
| `DB_USER` / `DB_PASSWORD` | `sa` / *(empty)* | SQL Server creds |
| `DB_TABLE` | `dbo.prodmauploadvakodata` | Ingest target table |
| `DB_DRIVER` | `ODBC Driver 17 for SQL Server` | pyodbc driver |
| `PG_ENABLED` / `PG_HOST` / `PG_PORT` | `true` / `localhost` / `5432` | App store toggle / host / port |
| `PG_USER` / `PG_PASSWORD` | `khem` / `Khem101$` | App store credentials |
| `PG_NAME` / `PG_SCHEMA` | `yinstagram` / `creatoros` | App database / schema |
| `S3_BUCKET` / `S3_REGION` | `veel-data-processing` / *(empty)* | S3 bucket/region |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | *(empty)* | S3 creds |
| `EXPORT_FORMATS` | `json,jsonl,csv` | Export formats |

Sessions can also be bulk-imported by placing them as `INSTA_SESSION_1`,
`INSTA_SESSION_2`, … with matching `INSTA_ACCOUNT_1`, `INSTA_ACCOUNT_2`, …
env variables pointing at `sessions/*.json` files.

## 6. Data layout

```
creatoros/
├── backend/            FastAPI (hexagonal) backend — app/, .env, run.sh
├── frontend/           Next.js dashboard (auth-gated)
├── pipeline/           user's analysis scripts + yolov8n.pt (analyzers delegate here)
├── sessions/           saved Instagram sessions (secret — gitignored)
├── data/
│   ├── postgres/       PostgreSQL DDL (schema/views/procedures/functions .sql)
│   ├── creatoros.db    SQLite fallback (jobs+projects+RBAC) when PG is unavailable
│   ├── scraper_data.db SQLite fallback profile metadata
│   └── Output_<project>/   input.csv, inputdone.csv, scraped DATA/, exports, charts
└── docs/               architecture + usage guides
```

The primary store is PostgreSQL (`yinstagram.creatoros`): jobs, projects,
project URLs, users, features, menus, audit_logs, connection_logs, api_traffic
and profiles. The SQLite files above exist only as a zero-config fallback.

PostgreSQL objects created on boot (visible in pgAdmin):

| Kind | Objects |
| ---- | ------- |
| Tables | `jobs`, `projects`, `project_urls`, `users`, `features`, `menus`, `audit_logs`, `connection_logs`, `api_traffic`, `profiles`, `app_meta` |
| Views | `v_jobs_by_status`, `v_dashboard_stats`, `v_recent_activity`, `v_profiles_by_followers` |
| Procedures | `creatoros.upsert_profile(...)`, `creatoros.record_audit(...)` |
| Functions | `creatoros.count_profiles()`, `creatoros.sum_media_count()`, `creatoros.top_profiles(n)`, `creatoros.search_profiles(q, n)` |

`features.roles` holds the comma-separated roles allowed per feature
(`admin,user` by default; `settings`/`admin`/`tracking` are `admin`). Every
`/api/*` call lands in `api_traffic` (user, method, path, status, latency, IP,
device, browser, OS) and signup/login land in `connection_logs` — viewable on
the **Tracking** page (`http://localhost:3000/tracking`).