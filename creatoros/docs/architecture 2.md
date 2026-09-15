# KreatOS — Architecture

## 1. Overview

CreatorOS is an Instagram creator intelligence platform. It does **not** embed
instagrapi into the UI. instagrapi is the *Instagram engine*, reached through a
thin adapter; everything else is an application built around it. From Phase 2
the app is an authenticated **admin tool**: the Selenium scraper, the ML
analyzer, CSV exports, SQL Server ingest and S3 storage all run as
UI-controllable jobs.

```
Browser (Next.js :3000)
   │   JWT bearer token over HTTPS
   ▼
FastAPI API (:8000)
   │  auth guard (every /api route)
   ▼
  Services      JobRunner / ProjectService / PipelineService / SettingsService
   │
   ├─► Instagram Adapter ─────────► instagrapi            (private API)
   ├─► ScraperAdapter   ─────────► Selenium (mirrors pipeline/*.py)
   ├─► AnalyzerAdapter  ─────────► pipeline/*.py + YOLOv8
   ├─► ExporterAdapter  ─────────► data/Output_<project>/
   ├─► DatabaseService  ─────────► local SQLite + remote SQL Server
   └─► StorageService   ─────────► S3 (bucket veel-data-processing)
```

The most important rule: **nothing outside `app/adapters/secondary/` knows of
instagrapi, Selenium, pyodbc or boto3.** Each external system is behind one
adapter.

## 2. Hexagonal (ports & adapters) layout

Dependencies point **inward**: the core knows nothing about the outside world;
adapters know about the core.

```
                          ┌──────────────────────────────┐
                          │        Kernel (core)         │
                          │  domain  ← pure entities     │
                          │  ports   ← interfaces        │
                          │  services ← use cases        │
                          └──────────────┬───────────────┘
                              depends on │ interfaces only
       ┌──────────────────────────────────┼──────────────────────────────┐
       ▼                                  ▼                              ▼
PRIMARY adapters                 SECONDARY adapters                runtime/infra
FastAPI routes ──► JobRunner    InstagrapiAdapter             ──► Instagram (private)
JWT guard         + services    FileSessionStore              ──► sessions/*.json
                                ScraperAdapter                ──► Selenium (pipeline)
                                AnalyzerAdapter               ──► pipeline/*.py, YOLOv8
                                JsonExporter/Jsonl/Csv        ──► data/Output_<project>/
                                SqliteJobStore/ProjectStore    ──► data/creatoros.db
                                InMemorySettingsStore          ──► backend/.env (read/write)
                                EnvSessionSource               ──► backend/.env (INSTA_*) + sessions/
                                ScraperSqliteAdapter           ──► data/scraper_data.db
                                SqlServerAdapter               ──► CreatorsDatabase (pyodbc)
                                S3StorageAdapter               ──► veel-data-processing (boto3)
```

| Layer | Path | Responsibility |
| ----- | ---- | -------------- |
| Domain | `app/core/domain/` | Pure entities (`Creator`, `CreatorPost`, `Account`, `Project`, `Job`, `SettingsSnapshot`, `Session`) |
| Ports | `app/core/ports/` | Interfaces for instagram, sessions, projects, jobs, pipeline, settings, database, storage |
| Services | `app/core/services/` | Use cases + `JobRunner` (threads for jobs) |
| Primary adapters | `app/adapters/primary/api/` | FastAPI routes, schemas, JWT `require_admin` dependency |
| Secondary adapters | `app/adapters/secondary/` | Adapters for each external system |
| Composition root | `app/main.py` | Wires adapters → services → 9 routers |

### Rules

- **The dependency rule.** `core` never imports from `adapters`; `main.py` is
  the only module that imports from both sides.
- **No external SDK outside its adapter.** `instagrapi`, `selenium`,
  `pyodbc`, `boto3` are importable only from their owning adapter.
- **Use cases take interfaces.** Every service receives a port; swapping SQL
  Server for Postgres or S3 for local disk is one new adapter + one line in
  `main.py`.

## 3. Runtime flow

### Auth (all `/api/*` routes except login)

```
POST /api/auth/login {email, password}
   ▶ verify against admin_email / password hash
   ▶ sign JWT (PyJWT, HS256, 12h default)
Browser stores token in localStorage and sends  Authorization: Bearer <jwt>.
GET /api/auth/me          → build_require_admin() dependency checks the token
```

### A job (e.g. scrape, analyze, export, full, index, ingest, s3_upload)

```
POST /api/jobs {kind, project?}
   ▶ ProjectService ensures project exists
   ▶ PipelineService.write_input_file(project)  → data/Output_<name>/input.csv
   ▶ JobRunner starts a thread → job.status = running
   ▶ adapter executes:
       scrape    → ScraperAdapter → selenium → scraper_data.db + scraped DATA/<username>
       analyze   → AnalyzerAdapter → pipeline/*.py + YOLOv8 → Excel + charts
       export    → ExporterAdapter → data/Output_<name>/<format>/
       index     → pipeline/index → S3-managed workplace index
       ingest    → SqlServerAdapter → SELECT column probe → INSERT/UPSERT to prodmauploadvakodata
       s3_upload → S3StorageAdapter → sync local project data to bucket
   ▶ job.status = success | failed, job output + logs updated
GET /api/jobs         → live polled by the frontend (2.5s interval)
```

### Database + storage are both *status + availability*

`GET /api/database` reports `local` (data/creatoros.db) and `remote`
(SQL Server connectivity) in one shot; `GET /api/storage` reports S3
connectivity and lists keys under a prefix.

## 4. Directory map (Phase 1 + 2)

```
creatoros/
├── backend/
│   ├── app/
│   │   ├── main.py                       # composition root + FastAPI app (9 routers)
│   │   ├── core/
│   │   │   ├── config.py                 # pydantic-settings + all Phase-2 vars
│   │   │   ├── domain/                   # Creator, CreatorPost, Account, Project,
│   │   │   │                             #   Job, SettingsSnapshot, Session, ProfileRecord
│   │   │   ├── ports/                    # instagram, session_store, project_store,
│   │   │   │                             #   job_store, pipeline, settings, database, storage
│   │   │   └── services/                 # instagram, account, project, job, pipeline,
│   │   │                                 #   settings, session, database, storage + JobRunner
│   │   └── adapters/
│   │       ├── primary/api/
│   │       │   ├── deps.py               # build_require_admin() (JWT)
│   │       │   ├── schemas.py
│   │       │   └── routes/               # auth, accounts, creators, projects, jobs,
│   │       │                             #   settings, sessions, database, storage
│   │       └── secondary/
│   │           ├── auth/                 # JwtAuthService
│   │           ├── store/                # sqlite JobStore + ProjectStore (data/creatoros.db)
│   │           ├── settings/             # InMemorySettingsStore (read/writes backend/.env)
│   │           ├── pipeline/             # pipeline_source (reads pipeline dir),
│   │           │                         #   sessions.py (INSTA_SESSION_* env → sessions)
│   │           ├── database/             # sqlite store, scraper_store (scraper_data.db),
│   │           │                         #   sqlserver.py (pyodbc, lazy)
│   │           ├── storage/              # s3.py (boto3, lazy)
│   │           ├── scraper/              # ScraperAdapter (Selenium)
│   │           ├── analyzer/             # AnalyzerAdapter (delegates to pipeline/*.py)
│   │           ├── exporters/            # json / jsonl / csv
│   │           ├── instagrapi/           # client.py (InstagramPort)
│   │           └── sessions/             # file_store.py
│   ├── requirements.txt
│   ├── run.sh
│   └── .env / .env.example
├── frontend/                             # Next.js: AuthGate guard + 9 pages
├── pipeline/                             # user's scripts (run_pipeline.py, *scraper.py,
│   │                                     #   csvmaker.py, iso3166_alpha2.py, yolov8n.pt …)
├── sessions/                             # instagrapi session files (gitignored, secret)
├── data/                                 # creatoros.db, scraper_data.db, Output_<project>/
└── docs/
```

## 5. Security

- **Admin login.** `POST /api/auth/login` verifies `admin_email` +
  `admin_password` (or `admin_password_hash` if set). Every other `/api/*`
  route requires a valid JWT (`Authorization: Bearer …`).
- **Sessions are secrets.** `sessions/*` is gitignored; the EnvSessionSource
  ingests `INSTA_SESSION_N`/`INSTA_ACCOUNT_N` from `.env` (or uploaded files)
  at startup, and active/backup split is `settings.scraper_active_sessions`.
- **SQL / S3 creds** come from `.env` only, never hard-coded.
- Password is used once at login; only the instagrapi session state survives.

## 6. Access control (Phase 3)

The RBAC plane covers users, role-aware feature flags, permission-gated menus,
a full feature/menu map and an audit + connection/traffic trail. The frontend
reads the map from `/api/auth/me` and branches dashboards by role.

### Data model (PostgreSQL `yinstagram.creatoros`, SQLite fallback)

All runtime state lives in the app store. The default is a local PostgreSQL
database (`PG_*` from `.env`); if it is unreachable at boot the API degrades
to the SQLite file (`data/creatoros.db`). DDL is kept in
`data/postgres/*.sql` and applied idempotently on every boot via
`app.adapters.secondary.postgres.connection.init_schema()` — schema, views,
stored procedures and functions are all provisioned in code and in pgAdmin.

```
users           id, email, name, role, status, password_hash, last_login
features        key, label, enabled, group_name, roles   ← on/off + allowed roles
menus           key, label, path, group_name, icon, position, feature
audit_logs      id, user, action, target, detail, created_at
connection_logs id, user, event, ip, user_agent, device, browser, os, location, created_at
api_traffic     id, user, email, method, path, status_code, duration_ms,
                ip, user_agent, device, browser, os, created_at
```

`features` and `menus` are seeded on boot (see
`app/core/domain/access.py`): 26 features across nine groups, plus 185 menu
rows. Each feature carries a comma-separated `roles` column (default
`admin,user`; `settings`, `admin` and `tracking` are `admin`-only) so a
feature can be both globally *enabled* and *role-gated*. Menu rows hang off a
feature (`key == feature` for the sidebar entry, `feature:<sub>` for in-page
tabs) so a disabled feature removes the whole branch from every client.

The menu map rebuild added `MARKETPLACE` (find / hashtags / locations / all /
saved / lists / creator-analysis) and `CAMPAIGNS` groups, plus `AUTOMATION`
(for jobs + monitoring). Engagement / direct / publishing default to
`enabled` so the full product tree is visible for both roles.

### Campaigns

Campaigns connect the saved profile store to outreach. Tables:
`campaigns` (brief: budget, location, audience keywords, min engagement,
status) and `campaign_creators` (a ranked, scored snapshot taken when
matching runs) + `campaign_requests` (outreach log).

- `POST /api/campaigns` — create a brief, `PATCH /{id}` edit, `DELETE /{id}`.
- `POST /api/campaigns/{id}/match` — `CampaignService.match` scores saved
  creators against the brief (audience keywords in bio/category, location,
  budget floor, engagement, verified/private) and persists the top N as
  ranked `CampaignCreator` rows; empty store degrades gracefully.
- Matching is heuristic v1: it runs against whatever the profile store holds
  today (the SQL Server ingest pipeline feeds it). With an empty store the
  UI surfaces guidance instead of fabricating results.
- Requests/creator statuses drive the Requests tab and the per-campaign
  outreach panels.
- Adapters: `PgCampaignStore` (Postgres) and `SqliteCampaignStore`
  (fallback); both implement `app/core/ports/campaign.py`.
- The dashboard snapshot exposes `stats.campaigns` (total, matches,
  by_status) and a `discovery` panel (totals, categories, ranked candidates
  with score) from `DashboardService.discovery()`.

### Marketplace

Marketplace is the subcategorised front door to the saved profile store. Six
subcategories: **UGC creators, Influencers, Digital creators, Reel creators,
Bloggers, Generic users** (`app/core/services/marketplace_service.py`).

- `GET /api/marketplace/categories` — per-subcategory counts (generic = store
  total minus the five labelled ones).
- `GET /api/marketplace/creators?category=` — saved profiles for a
  subcategory via `search_profiles_by_category`.
- `POST /api/marketplace/discover` — live Instagram discovery: the engine's
  `search_users_v1(query, count)` runs per subcategory, non-private hits are
  upserted into the store with the subcategory label as their `category`
  (collision with Instagram category names is acceptable, since filtering is
  by exact label). Unauthenticated instagrapi fails cleanly (`login_required`
  → 400 with guidance).
- `POST /api/marketplace/save` — typed upsert of a creator record (used by the
  creator profile's Save button).
- All routes are gated on the `marketplace` feature (empty store → honest
  empty states; no fabricated data).
- Store support: `upsert_profile(record)`, `count_profiles_by_category`,
  `search_profiles_by_category` on `DatabasePort` — implemented by
  `ScraperSqliteAdapter` (SQLite `ON CONFLICT (username)` upsert) and
  `PgProfileStore` (CALL `creatoros.upsert_profile(...)` + ILIKE filters).
- The creator profile page (`/creators/{username}`) reads the same records:
  header (avatar, name, bio, location when available) with **[Analyze]**
  (live `get_creator` + recent posts) and **[Save]** (marketplace upsert),
  then a stat row — Followers / Following / Posts / **Engagement %**
  (avg-likes ÷ followers) — plus a Performance card and a Recent Content grid.

### Roles & self-signup

Every identity is a row in `users` with a role (`admin` | `user`).
`POST /api/auth/signup` (open to the platform) creates a `user` — passwords
stored only as PBKDF2 hashes, signup audited and logged as a connection. Only
the environment admin (`ADMIN_EMAIL`) is ever provisioned `admin`, so the
admin/feature/settings/tracking modules stay out of reach of self-registered
users. `GET /api/admin/users` lists identities for the admin.

### Enforcement is server-side

`build_require_feature(require_admin, admin_service)` returns a dependency
factory. Each router registers one, e.g.
`dependencies=[Depends(require_feature("creators"))]`. A disabled feature or a
role not listed in the feature's `roles` → **403 before the route runs**;
hiding the menu in the UI is never the security boundary.

```
Browser → JWT → require_admin → require_feature("<key>") → route → service → adapter
```

### Connection & API traffic tracking

- `app.adapters.primary.api.clientinfo` parses the User-Agent into
  device/browser/OS, reads the client IP (X-Forwarded-For → X-Real-IP →
  socket) and best-effort resolves a city/country via ip-api.com (cached,
  2 s timeout, private IPs skipped).
- A `@app.middleware("http")` in `main.py` records **every `/api/*` call**
  into `api_traffic` (user from JWT or `anonymous`, method, path, status,
  latency, client). Failures are swallowed so tracking can never break a request.
- Signup/login record a row in `connection_logs` from the auth router.
- `GET /api/tracking/{traffic,connections,stats}` (admin + feature `tracking`)
  expose the trail; the `/tracking` page renders stats, latency, status
  distributions and client detail.

### Bootstrap contract for the UI

- `GET /api/auth/me` → `{email, role, name, features[], menus{group:[…]}}` —
  filters features/menus by the caller's role, driving the dynamic grouped
  sidebar (root items only) and the role-branched home page.
- `POST /api/auth/signup` → `{token, email, role}` — self-registration.
- `GET /api/admin/features` + `PUT /api/admin/features/{key}` — flip flags;
  every gated route + menu reacts immediately.
- `GET /api/admin/audit`, `GET /api/admin/users` — who did what, and who exists.
- `GET /api/dashboard` → control-center aggregates:
  `{stats{creators, posts_analyzed, accounts, storage_available, jobs…},
    top_creators[], recent_activity[]}` (cold COUNT / LIMIT reads).

## 7. Technology choices

| Concern | Choice |
| ------- | ------ |
| HTTP API | FastAPI + Uvicorn |
| Config | pydantic-settings (`.env`), writable at runtime |
| Admin auth | PyJWT (HS256) bearer tokens |
| App store | PostgreSQL `yinstagram.creatoros` via psycopg2 (SQLite fallback), DDL in `data/postgres/*.sql` |
| Job state | Postgres `jobs` table + threaded JobRunner |
| Instagram engine | instagrapi 2.x (private API) |
| Scraper | Selenium (mirrors user pipeline scripts) |
| Analyzer | pipeline/*.py + YOLOv8 (`pipeline/yolov8n.pt`) |
| Remote database | SQL Server via pyodbc (`CreatorsDatabase.dbo.prodmauploadvakodata`) |
| Storage | S3 via boto3 (`veel-data-processing`) |
| Session persistence | JSON under `sessions/`, env-importable |
| Frontend | Next.js (App Router) + Tailwind + localStorage JWT |
| Language | Python 3.10+ / TypeScript |