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
│   ├── frontend/       Next.js dashboard
│   ├── sessions/       saved Instagram sessions (secret)
│   ├── data/           exported data
│   └── docs/           architecture + usage documentation
│
└── instagrapi/         the Instagram engine (Python library)
```

`instagrapi/` is treated as an engine: only
`creatoros/backend/app/adapters/secondary/instagrapi/` imports it. Everything
else in CreatorOS talks to the rest of the system through interfaces
(`creatoros/backend/app/core/ports/`). The `examples/` and `tests/` folders
belong to the underlying instagrapi library.

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

- [Architecture](creatoros/docs/architecture.md) — hexagonal design, layers, data flow, replacing the engine
- [Usage](creatoros/docs/usage.md) — setup, run, API reference, sessions, configuration

## Status (Phase 1)

- [x] Hexagonal FastAPI backend
- [x] Creator lookup API (profile + posts)
- [x] Account manager with persistent sessions
- [x] Next.js dashboard (creator search, analysis, CSV export, account UI)
- [ ] Postgres creator database
- [ ] Job/worker system
- [ ] Creator scoring & campaign matching

## About instagrapi

[instagrapi] is an unofficial Instagram private API wrapper (MIT licensed,
included at the repository root). It powers the Instagram connector; see
[Docs/Architecture](creatoros/docs/architecture.md) for how it is isolated
behind a port. Note that private-API automation is fragile and subject to
Instagram behavior changes — it is intended for controlled, internal use.

[instagrapi]: https://github.com/subzeroid/instagrapi


find . -type f \( -name ".env" -o -name "*.session" -o -name "*cookie*" -o -name "*.pem" -o -name "*.key" \) -not -path "./.git/*"