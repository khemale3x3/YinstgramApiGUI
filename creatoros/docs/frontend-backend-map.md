# KreatOS — Frontend → Backend Map

Frontend: Next.js 16 (Turbopack), `frontend/src/lib/api.ts` is the single API client.
`frontend/src/components/ui.tsx` provides Card/Input/Btn/StatCard/etc.

| Page (route) | Component | API client function(s) | Endpoint(s) | Backend entity |
| ------------ | --------- | ---------------------- | ----------- | -------------- |
| `/` (Dashboard) | page.tsx AdminHome | getDashboard, listJobs(8) | /api/dashboard, /api/jobs | profiles, jobs, audit_logs, campaigns |
| `/creators` | creators/page.tsx | searchProfiles, topProfiles, marketplaceCreators | /api/database/search, /api/database/top, /api/marketplace/creators | profiles |
| `/creators/[creatorId]` | creators/[creatorId]/page.tsx | getCreator, getCreatorPosts, marketplaceSave | /api/creators/{user}, /api/creators/{user}/posts, /api/marketplace/save | live IG + profiles |
| `/discovery` | discovery/page.tsx (TabbedModule) | adminMe (menus) | /api/auth/me | features, menus |
| `/analytics` | analytics/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/content` | content/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/hashtags` | hashtags/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/locations` | locations/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/collections` | collections/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/notes` | notes/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/engagement` | engagement/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus |
| `/direct` | direct/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus *(feature disabled)* |
| `/publishing` | publishing/page.tsx (TabbedModule) | adminMe | /api/auth/me | features, menus *(feature disabled)* |
| `/accounts` | accounts/page.tsx | getAccounts, checkAccount, importSessionsEnv | /api/accounts, /api/accounts/{u}/check, /api/sessions/import | sessions / accounts |
| `/sessions` | sessions/page.tsx | getSessions, importSessionsEnv, createInstagrapiSession | /api/sessions, /api/sessions/import, /api/sessions/instagrapi | sessions |
| `/marketplace` | marketplace/page.tsx | marketplaceCategories, marketplaceCreators, marketplaceDiscover, marketplaceSave | /api/marketplace/* | profiles |
| `/campaigns` | campaigns/page.tsx, campaigns/[id]/page.tsx, campaigns/[id]/matching | listCampaigns, getCampaign, campaignMatch, campaignRequest, updateCampaignCreator | /api/campaigns/* | campaigns, campaign_creators, campaign_requests |
| `/projects` | projects/page.tsx | listProjects, createProject, getProject, uploadUrls, listUrls | /api/projects/* | projects, project_urls |
| `/data` | data/page.tsx | ingestDatabase (jobs) | /api/jobs | jobs |
| `/database` | database/page.tsx | databaseStatus, databaseViews, databaseTables, searchProfiles, recentProfiles | /api/database/* | all creatoros tables + views |
| `/storage` | storage/page.tsx | storageStatus, listS3Keys, uploadS3, downloadS3Key | /api/storage/* | s3 |
| `/jobs` | jobs/page.tsx | listJobs, createJob, cancelJob, deleteJob, retryJob, listProjects | /api/jobs/*, /api/projects | jobs |
| `/monitoring` | monitoring/page.tsx | listJobs, getDashboard | /api/jobs, /api/dashboard | jobs, profiles |
| `/settings` | settings/page.tsx | getSettings, updateSettings, adminMe, adminFeatures | /api/settings, /api/auth/me, /api/admin/features | config/env + features |
| `/admin` | admin/page.tsx | adminUsers, adminFeatures, adminSetFeature, adminAuditLogs, adminMenus, getDashboard | /api/admin/*, /api/dashboard | users, features, menus, audit_logs |
| `/tracking` | tracking/page.tsx | trackingStats, trackingTraffic, trackingConnections | /api/tracking/* | api_traffic, connection_logs |

## Connection honesty

- **Fully connected**: Dashboard, Creators, Marketplace, Jobs, Projects, Database,
  Storage, Monitoring, Settings, Admin, Tracking, Accounts, Sessions, Campaigns, Data.
- **Module-map placeholders** (`TabbedModule`): Discovery, Analytics, Content, Hashtags,
  Locations, Collections, Notes, Engagement, Direct, Publishing. These render the *real*
  backend menu/submenu tree and state they are workflow placeholders — no fake data.
- **Direct + Publishing**: feature-flagged off (backend + menu), because the instagrapi
  adapter (`backend/app/adapters/secondary/instagrapi/client.py`) implements neither DMs
  nor media upload. They are never presented as working.

## Pagination

`searchProfiles / recentProfiles / topProfiles` accept `page` and return
`{ results, total, page, limit }`; the backend computes `offset = (page-1)*limit`
server-side (see `docs/api-routes.md`).