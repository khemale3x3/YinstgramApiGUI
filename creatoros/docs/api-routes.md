# KreatOS — API Routes

Base URL: `http://127.0.0.1:8000`. Auth: `Authorization: Bearer <token>` from
`POST /api/auth/login`. Feature-gated routers return `403 {"detail":"feature disabled"}`
when the flag is off; admin-only routes return `403` for non-admins.

| Method | Path | Feature gate | Admin-only | Service | Backend tables |
| ------ | ---- | ------------ | ---------- | ------- | -------------- |
| POST | /api/auth/login | — | no | AuthService | users, connection_logs, audit_logs, api_traffic |
| POST | /api/auth/signup | — | no | AuthService | users, connection_logs |
| GET | /api/auth/me | — | no | AuthService + AdminService | users, features, menus |
| GET | /api/creators | creators | yes | InstagramService (instagrapi) | (live IG) |
| GET | /api/creators/{username} | creators | yes | InstagramService | (live IG) |
| GET | /api/creators/{username}/posts | creators | yes | InstagramService | (live IG) |
| GET | /api/accounts | accounts | yes | AccountService | sessions/ |
| GET | /api/accounts/{username} | accounts | yes | AccountService | sessions/ |
| GET | /api/accounts/{username}/check | accounts | yes | AccountService | sessions/ |
| GET | /api/sessions | sessions | yes | SessionService | sessions/ |
| POST | /api/sessions/import | sessions | yes | SessionService | sessions dir |
| POST | /api/sessions/instagrapi | sessions | yes | SessionService | sessions dir |
| GET | /api/dashboard | dashboard | yes | DashboardService | profiles, jobs, audit_logs, campaigns, sessions, s3 |
| GET | /api/jobs | jobs | yes | JobService | jobs |
| POST | /api/jobs | jobs | yes | JobService → dispatch | jobs |
| GET | /api/jobs/{job_id} | jobs | yes | JobService | jobs |
| POST | /api/jobs/{job_id}/cancel | jobs | yes | JobService | jobs |
| POST | /api/jobs/{job_id}/retry | jobs | yes | JobService | jobs |
| GET | /api/projects | projects | yes | ProjectService | projects, project_urls |
| POST | /api/projects | projects | yes | ProjectService | projects |
| GET | /api/projects/{name} | projects | yes | ProjectService | projects, project_urls |
| GET | /api/projects/{name}/urls | projects | yes | ProjectService | project_urls |
| POST | /api/projects/{name}/urls/upload | projects | yes | ProjectService | project_urls |
| POST | /api/projects/{name}/urls | projects | yes | ProjectService | project_urls |
| GET | /api/projects/{name}/urls/failed | projects | yes | ProjectService | project_urls |
| DELETE | /api/projects/{name}/urls/remove | projects | yes | ProjectService | project_urls |
| GET | /api/settings | settings | yes | SettingsService | (env/config) |
| PATCH | /api/settings | settings | yes | SettingsService | (env/config) |
| GET | /api/database/status | database | yes | DatabaseService | profiles |
| GET | /api/database/search?q&page&limit | database | yes | DatabaseService | profiles |
| GET | /api/database/profiles/{username} | database | yes | DatabaseService | profiles |
| GET | /api/database/recent?page&limit | database | yes | DatabaseService | profiles |
| GET | /api/database/top?page&limit | database | yes | DatabaseService | profiles |
| GET | /api/database/tables | database | yes | DatabaseService | all creatoros tables |
| GET | /api/database/views | database | yes | DatabaseService | views |
| GET | /api/storage/status | storage | yes | StorageService | s3 |
| GET | /api/storage/list | storage | yes | StorageService | s3 |
| POST | /api/storage/upload | storage | yes | StorageService | s3 |
| GET | /api/storage/download | storage | yes | StorageService | s3 |
| GET | /api/admin | admin | yes | AdminService | users/features/menus counts |
| GET | /api/admin/users | admin | yes | AdminService | users |
| GET | /api/admin/features | admin | yes | AdminService | features |
| PUT | /api/admin/features/{key} | admin | yes | AdminService | features |
| GET | /api/admin/menus | admin | yes | AdminService | menus |
| GET | /api/admin/audit | admin | yes | AdminService | audit_logs |
| GET | /api/tracking/stats | tracking | yes | AdminService | api_traffic, connection_logs |
| GET | /api/tracking/traffic | tracking | yes | AdminService | api_traffic |
| GET | /api/tracking/connections | tracking | yes | AdminService | connection_logs |
| GET | /api/campaigns | campaigns | no | CampaignService | campaigns |
| POST | /api/campaigns | campaigns | admin | CampaignService | campaigns |
| GET | /api/campaigns/stats | campaigns | no | CampaignService | campaigns, campaign_creators |
| GET | /api/campaigns/{id} | campaigns | no | CampaignService | campaigns, campaign_creators |
| POST | /api/campaigns/{id}/match | campaigns | admin | CampaignService | campaign_creators |
| POST | /api/campaigns/{id}/request | campaigns | admin | CampaignService | campaign_requests |
| GET | /api/campaigns/{id}/requests/{username} | campaigns | admin | CampaignService | campaign_requests |
| PATCH | /api/campaigns/{id}/creators/{username} | campaigns | admin | CampaignService | campaign_creators |
| GET | /api/marketplace/categories | marketplace | no | MarketplaceService | profiles (category counts) |
| GET | /api/marketplace/creators | marketplace | no | MarketplaceService | profiles |
| POST | /api/marketplace/discover | marketplace | no | MarketplaceService + InstagramService | profiles (upsert) |
| POST | /api/marketplace/save | marketplace | no | MarketplaceService | profiles |
| GET | /health | — | no | — | — |
| GET | / | — | no | — | — |

Notes:
- Every `/api` call (except OPTIONS/HEAD) is recorded into `api_traffic` by the
  `record_api_traffic` middleware in `app/main.py`.
- All `/api/database/*`, `/api/jobs/*`, `/api/settings`, `/api/admin/*`, `/api/tracking/*`,
  `/api/storage/*`, `/api/sessions/*`, `/api/accounts/*`, `/api/creators/*` are
  admin-gated (`require_admin`).
- `direct` and `publishing` have **no** backend routers — the integration (instagrapi
  adapter) does not implement DMs or uploads, so those features are disabled and their
  menu items are hidden rather than faked.