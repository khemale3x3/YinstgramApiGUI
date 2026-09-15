# CreatorOS

**Instagram Creator Intelligence Platform.**

CreatorOS is a self-hosted platform for creator discovery, account management
and content intelligence. It is built **around** the [instagrapi] engine rather
than inside it, using a hexagonal (ports & adapters) backend so the Instagram
connector is a swappable adapter.

## What's in this repository

```
.
├── creatoros/          CreatorOS application
│   ├── backend/        FastAPI (hexagonal) API
│   ├── frontend/       Next.js dashboard (auth-guarded)
│   ├── pipeline/       analysis + scraper scripts (YOLOv8, CSV, indexing)
│   ├── sessions/       saved Instagram sessions (secret)
│   ├── data/           creatoros.db, scraper_data.db, project output
│   └── docs/           architecture + usage documentation
│
└── instagrapi/         the Instagram engine (Python library)
```

`instagrapi/` is treated as an engine: only
`creatoros/backend/app/adapters/secondary/instagrapi/` imports it. Everything
else in CreatorOS talks to the rest of the system through interfaces
(`app/core/ports/`).

## Quick start

**Backend (terminal 1):**

```bash
cd creatoros/backend
./run.sh
# API    → http://127.0.0.1:8000
# Swagger→ http://127.0.0.1:8000/docs
```

**Frontend (terminal 2):**

```bash
cd creatoros/frontend
npm install
npm run dev
# Dashboard → http://localhost:3000
```

## Documentation

- [Architecture](creatoros/docs/architecture.md) — hexagonal design, layers, routing, replacing the engine
- [Usage](creatoros/docs/usage.md) — setup, run, API reference, sessions, configuration

## Status (Phase 3)

- [x] Hexagonal FastAPI backend
- [x] PostgreSQL app store — `yinstagram.creatoros`, DDL in `data/postgres/*.sql`
      (schema, views, stored procedures, functions), auto-applied on every boot
- [x] Creator lookup API (profile + posts) — retained in the Dashboard's Creator Discovery panel
- [x] Account manager with persistent sessions
- [x] Admin authentication (JWT) — every `/api/*` route gated
- [x] Projects + URL lists (`input.csv`), threaded JobRunner
- [x] Jobs: scrape (Selenium), analyze (YOLOv8 + pipeline), export, full, index, ingest (SQL Server), s3_upload
- [x] Settings page that reads/writes `backend/.env`
- [x] Sessions manager (active/backup, env import)
- [x] Database page (local SQLite + remote SQL Server status/search)
- [x] Storage page (S3 status, key browser, upload/download)
- [x] RBAC — users/features/menus/audit tables, per-feature `roles` column,
      server-side feature gates (`403`)
- [x] Self-signup (`POST /api/auth/signup`) — new users get role `user`;
      only the env admin is ever `admin`
- [x] Role-aware UI — user workspace vs admin control-center home; admin-only
      modules (settings/administration/tracking) hidden + hard-blocked
- [x] Connection + API-traffic tracking — signup/login rows and every `/api/*`
      call recorded with IP, device, browser, OS and location
- [x] Tracking page (`/tracking`) — traffic/connection tables + latency/status stats
- [x] Feature Controls + Users + Audit Log admin pages
- [x] Control-center Dashboard (aggregates, top creators, recent activity, system health)
- [x] Dynamic grouped sidebar (root menu items served from `/api/auth/me`,
      filtered by enabled features + role)
- [x] Complete feature/menu map — 26 features, 185 menu rows across nine
      groups (incl. Marketplace + Campaigns + Automation); module pages use
      their `feature:<sub>` rows as in-page tabs
- [x] Module pages (discovery/content/hashtags/locations/analytics/collections/notes/
      engagement/direct/publishing) + Monitoring, Import/Export, Tracking
- [x] Unified Discovery — search saved creators by username/category/audience
- [x] Marketplace — subcategory browsing (UGC creators, Influencers, Digital
      creators, Reel creators, Bloggers, Generic users) with live Instagram
      discovery + save; find/all/saved tabs, creator lists, analysis
- [x] Creator profile as main object — `/creators/{username}` with avatar/name/
      bio header, [Analyze] and [Save] actions, stat row (Followers / Following /
      Posts / Engagement %), Performance card (Followers, Engagement, Avg Likes),
      Recent Content grid, and Overview/Posts/Reels/Stories/Analytics/Audience/
      Campaigns/History tabs
- [x] Campaigns — briefs, DB-backed CRUD (`campaigns`, `campaign_creators`,
      `campaign_requests`) with ranking + matching screen + outreach requests
- [x] Dashboard upgrade — campaigns stat, Creator Discovery panel, Top Creators
      with score
- [x] Next.js dashboard (auth-guarded, 31 pages)
- [x] Hydration-safe login gate (deterministic SSR, no token reads during render)
- [x] Login reliability — clear "Cannot reach the API" message, CORS for both `localhost` and `127.0.0.1`
- [ ] Admin user management UI (list exists via API; promote/disable ships next)
- [ ] Real profile data pipeline — marketplace **Discover** populates the store
      live, but a full analyze/scrape or SQL Server ingest is still the reliable
      bulk path (matching/discovery surfaces guidance meanwhile)

[instagrapi]: https://github.com/subzeroid/instagrapi