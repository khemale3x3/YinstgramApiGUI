# KreatOS — RBAC, Features & Permissions

## Model

- `users.role` ∈ `admin` | `user`. Bootstrap admin comes from `ADMIN_EMAIL`/`ADMIN_PASSWORD`
  (hashed with bcrypt via `AuthService`) — stored hashes only, never plaintext.
- `features` = global feature flags with `roles` (comma-separated roles allowed) and
  `enabled` (off = hidden from menu + 403 from backend).
- `menus` = one menu definition (`key`, `label`, `path`, `group_name`, `icon`, `position`,
  `feature`). The sidebar is generated **dynamically** from `GET /api/auth/me` →
  `{ user, features, menus }` filtered by role + feature enabled → one sidebar for all
  roles, no hardcoded per-role sidebars.
- Enforcement is **backend-first**: `build_require_feature(key)` (deps.py) sits in each
  router's dependencies and returns 403 when disabled; `require_admin` gates admin routes.
  Frontend hiding is cosmetic, never security.

## Feature → roles → backend enforcement

| Feature | Group | Default | Roles | Backend router gate |
| ------- | ----- | ------- | ----- | ------------------- |
| dashboard | Main | on | admin,user | /api/dashboard (require_admin) |
| creators | Intelligence | on | admin,user | /api/creators/* (require_admin) |
| discovery | Intelligence | on | admin,user | none (module map) |
| content | Intelligence | on | admin,user | none (module map) |
| hashtags | Intelligence | on | admin,user | none (module map) |
| locations | Intelligence | on | admin,user | none (module map) |
| analytics | Intelligence | on | admin,user | none (module map) |
| collections | Intelligence | on | admin,user | none (module map) |
| notes | Intelligence | on | admin,user | none (module map, no DB table yet) |
| engagement | Engagement | on | admin,user | none (module map) |
| **direct** | Engagement | **off** | admin,user | no router — unsupported integration |
| **publishing** | Engagement | **off** | admin,user | no router — unsupported integration |
| accounts | Accounts | on | admin,user | /api/accounts/* |
| sessions | Accounts | on | admin,user | /api/sessions/* |
| marketplace | Marketplace | on | admin,user | /api/marketplace/* |
| campaigns | Campaigns | on | admin,user | /api/campaigns/* (+ admin for writes) |
| projects | Data | on | admin,user | /api/projects/* |
| data | Data | on | admin,user | via jobs |
| database | Data | on | admin,user | /api/database/* |
| storage | Data | on | admin,user | /api/storage/* |
| automation | Automation | on | admin,user | none (module map) |
| jobs | Automation | on | admin,user | /api/jobs/* (require_admin) |
| monitoring | Automation | on | admin,user | via /api/jobs + /api/dashboard |
| settings | System | on | **admin** | /api/settings/* (require_admin) |
| admin | System | on | **admin** | /api/admin/* (require_admin) |
| tracking | System | on | **admin** | /api/tracking/* (require_admin) |

## Feature → Permission mapping (conceptual)

The app uses role + feature-flag gating rather than a separate `permissions` table. The
intent matrix for future granular perms:

```text
creator.view|search|create|edit|delete|import|export|analyze|bulk   → Creators, Database
analytics.view|create_report|export                                  → Analytics
account.view|connect|validate|health|remove                          → Accounts, Sessions
publishing.view|create|delete                                        → publishing (off)
job.view|create|cancel|retry                                         → Jobs
```

To add granular permissions later: introduce `permissions` + `role_permissions` +
`user_permissions` tables and a `require_perm(key)` dependency mirroring
`build_require_feature` (`app/adapters/primary/api/deps.py`).

## Account-level access & tenant isolation

Not yet modeled — no `user_account_access` / workspace tables exist; users share one
workspace. Enabling this later = new tables + a `require_account(username)` dependency.

## Admin surfaces

- `GET /api/admin` overview, `/api/admin/users`, `/api/admin/features` + PUT toggle,
  `/api/admin/menus`, `/api/admin/audit`.
- `GET /api/admin/features` returns the 26 flags with roles; `PUT /api/admin/features/{key}`
  toggles `enabled` (audited). Direct + Publishing are reserved in the DB as **disabled**
  until a DM/upload integration exists.

## Audit

`audit_logs` records login, signup, feature toggles and admin actions (user, action,
target, detail, created_at). `api_traffic` + `connection_logs` capture HTTP + auth events.
No secrets or credentials are ever written to logs.