"""RBAC + feature-flag domain entities + the full CreatorOS map.

CreatorOS models access control as users with a role, global feature flags
(with the roles allowed to use each feature), permission-gated menus and an
audit + connection/traffic trail. Authorization is validated server-side
(`require_feature`) so hiding a menu in the frontend is never the security
boundary.

Menus: the top-level item per feature (key == feature) is what the sidebar
renders; the `feature:<sub>` items form the in-page tab map, so the complete
feature/menu map lives in the database for admin screens and future use.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class User:
    id: str
    email: str
    name: str = ""
    username: str = ""
    role: str = "user"
    status: str = "active"          # active | disabled
    created_at: str = ""
    last_login: str = ""
    password_hash: str = ""


@dataclass
class FeatureFlag:
    key: str
    label: str
    enabled: bool = False
    group: str = "General"
    roles: str = "admin,user"       # comma-separated role names allowed


@dataclass
class MenuItem:
    key: str
    label: str
    path: str
    group: str
    icon: str = "•"
    order: int = 0
    feature: str = ""


@dataclass
class AuditLog:
    id: str
    user: str = ""
    action: str = ""
    target: str = ""
    detail: str = ""
    created_at: str = ""


@dataclass
class TrackedEvent:
    id: str
    user: str = ""
    email: str = ""
    action: str = ""                # event kind for connections / http for traffic
    method: str = ""
    path: str = ""
    status: int = 0
    duration_ms: int = 0
    ip: str = ""
    user_agent: str = ""
    device: str = ""
    browser: str = ""
    os: str = ""
    location: str = ""
    created_at: str = ""


# ------------------------------------------------------------------ seed data
# group values mirror the sidebar sections (MAIN / INTELLIGENCE /
# ENGAGEMENT / ACCOUNTS / MARKETPLACE / CAMPAIGNS / DATA / AUTOMATION / SYSTEM).
FEATURES: list[FeatureFlag] = [
    FeatureFlag("dashboard", "Dashboard", enabled=True, group="Main", roles="admin,user"),
    # ---------------------------------------------- intelligence (read/monitor)
    FeatureFlag("creators", "Creators", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("scraper", "Scraper", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("discovery", "Discovery", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("content", "Content", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("hashtags", "Hashtags", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("locations", "Locations", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("analytics", "Analytics", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("collections", "Collections", enabled=True, group="Intelligence", roles="admin,user"),
    FeatureFlag("notes", "Notes", enabled=True, group="Intelligence", roles="admin,user"),
    # --------------------------------------- engagement (off unless integration supports)
    # The instagrapi adapter (app/adapters/secondary/instagrapi/client.py) only
    # reads public/authorized data: profile info, media, user search, session
    # validation. Direct-messaging and publishing are NOT implemented by the
    # adapter, so they stay disabled — the menu is hidden and routes 403 until
    # an upload/DM-capable integration is wired in.
    FeatureFlag("engagement", "Engagement", enabled=True, group="Engagement", roles="admin,user"),
    FeatureFlag("direct", "Direct Messages", enabled=False, group="Engagement", roles="admin,user"),
    FeatureFlag("publishing", "Publishing", enabled=False, group="Engagement", roles="admin,user"),
    # ---------------------------------------------------------------- accounts
    FeatureFlag("accounts", "Accounts", enabled=True, group="Accounts", roles="admin,user"),
    FeatureFlag("sessions", "Sessions", enabled=True, group="Accounts", roles="admin,user"),
    # ------------------------------------------------- marketplace + campaigns
    FeatureFlag("marketplace", "Marketplace", enabled=True, group="Marketplace", roles="admin,user"),
    FeatureFlag("campaigns", "Campaigns", enabled=True, group="Campaigns", roles="admin,user"),
    # -------------------------------------------------------------------- data
    FeatureFlag("projects", "Projects", enabled=True, group="Data", roles="admin,user"),
    FeatureFlag("data", "Import / Export", enabled=True, group="Data", roles="admin,user"),
    FeatureFlag("database", "Database", enabled=True, group="Data", roles="admin,user"),
    FeatureFlag("storage", "Storage", enabled=True, group="Data", roles="admin,user"),
    # -------------------------------------------------------------- automation
    FeatureFlag("automation", "Automation", enabled=True, group="Automation", roles="admin,user"),
    FeatureFlag("jobs", "Background Jobs", enabled=True, group="Automation", roles="admin,user"),
    FeatureFlag("monitoring", "Monitoring", enabled=True, group="Automation", roles="admin,user"),
    # ------------------------------------------------------------------ system
    FeatureFlag("settings", "Settings", enabled=True, group="System", roles="admin"),
    FeatureFlag("admin", "Administration", enabled=True, group="System", roles="admin"),
    FeatureFlag("tracking", "Tracking", enabled=True, group="System", roles="admin"),
]


MENU_ITEMS: list[MenuItem] = [
    # ------------------------------------------------------------------- main
    MenuItem("dashboard", "Dashboard", "/", "MAIN", icon="🏠", order=10, feature="dashboard"),
    MenuItem("dashboard:overview", "Overview", "/", "MAIN", order=11, feature="dashboard"),
    MenuItem("dashboard:activity", "Activity", "/", "MAIN", order=12, feature="dashboard"),
    MenuItem("dashboard:health", "System Health", "/", "MAIN", order=13, feature="dashboard"),
    MenuItem("dashboard:jobs", "Jobs", "/", "MAIN", order=14, feature="dashboard"),
    MenuItem("dashboard:alerts", "Alerts", "/", "MAIN", order=15, feature="dashboard"),
    # ---------------------------------------------------------- intelligence
    MenuItem("creators", "Creators", "/creators", "INTELLIGENCE", icon="👤", order=20, feature="creators"),
    MenuItem("creators:all", "All Creators", "/creators", "INTELLIGENCE", order=21, feature="creators"),
    MenuItem("creators:search", "Search Creators", "/creators", "INTELLIGENCE", order=22, feature="creators"),
    MenuItem("creators:profile", "Creator Profile", "/creators", "INTELLIGENCE", order=23, feature="creators"),
    MenuItem("creators:posts", "Creator Posts", "/creators", "INTELLIGENCE", order=24, feature="creators"),
    MenuItem("creators:reels", "Reels", "/creators", "INTELLIGENCE", order=25, feature="creators"),
    MenuItem("creators:stories", "Stories", "/creators", "INTELLIGENCE", order=26, feature="creators"),
    MenuItem("creators:highlights", "Highlights", "/creators", "INTELLIGENCE", order=27, feature="creators"),
    MenuItem("creators:followers", "Followers", "/creators", "INTELLIGENCE", order=28, feature="creators"),
    MenuItem("creators:following", "Following", "/creators", "INTELLIGENCE", order=29, feature="creators"),
    MenuItem("creators:tagged", "Tagged", "/creators", "INTELLIGENCE", order=30, feature="creators"),
    MenuItem("creators:mentions", "Mentions", "/creators", "INTELLIGENCE", order=31, feature="creators"),
    MenuItem("creators:analytics", "Creator Analytics", "/creators", "INTELLIGENCE", order=32, feature="creators"),
    MenuItem("scraper", "Scraper", "/scraper", "INTELLIGENCE", icon="⚙", order=35, feature="scraper"),
    MenuItem("scraper:instagram", "Instagram Scraper", "/scraper", "INTELLIGENCE", order=36, feature="scraper"),
    MenuItem("scraper:network", "Followers / Followings Scraper", "/scraper", "INTELLIGENCE", order=37, feature="scraper"),

    MenuItem("discovery", "Discovery", "/discovery", "INTELLIGENCE", icon="🔎", order=40, feature="discovery"),
    MenuItem("discovery:users", "User Search", "/discovery", "INTELLIGENCE", order=41, feature="discovery"),
    MenuItem("discovery:accounts", "Account Search", "/discovery", "INTELLIGENCE", order=42, feature="discovery"),
    MenuItem("discovery:media", "Media Search", "/discovery", "INTELLIGENCE", order=43, feature="discovery"),
    MenuItem("discovery:reels", "Reel Search", "/discovery", "INTELLIGENCE", order=44, feature="discovery"),
    MenuItem("discovery:top", "Top Search", "/discovery", "INTELLIGENCE", order=45, feature="discovery"),
    MenuItem("discovery:typeahead", "Typeahead", "/discovery", "INTELLIGENCE", order=46, feature="discovery"),
    MenuItem("discovery:suggested", "Suggested Accounts", "/discovery", "INTELLIGENCE", order=47, feature="discovery"),
    MenuItem("discovery:similar", "Similar Creators", "/discovery", "INTELLIGENCE", order=48, feature="discovery"),
    MenuItem("discovery:recommended", "Recommended Accounts", "/discovery", "INTELLIGENCE", order=49, feature="discovery"),

    MenuItem("content", "Content", "/content", "INTELLIGENCE", icon="📸", order=60, feature="content"),
    MenuItem("content:posts", "Posts", "/content", "INTELLIGENCE", order=61, feature="content"),
    MenuItem("content:photos", "Photos", "/content", "INTELLIGENCE", order=62, feature="content"),
    MenuItem("content:videos", "Videos", "/content", "INTELLIGENCE", order=63, feature="content"),
    MenuItem("content:reels", "Reels", "/content", "INTELLIGENCE", order=64, feature="content"),
    MenuItem("content:albums", "Albums", "/content", "INTELLIGENCE", order=65, feature="content"),
    MenuItem("content:igtv", "IGTV", "/content", "INTELLIGENCE", order=66, feature="content"),
    MenuItem("content:stories", "Stories", "/content", "INTELLIGENCE", order=67, feature="content"),
    MenuItem("content:highlights", "Highlights", "/content", "INTELLIGENCE", order=68, feature="content"),
    MenuItem("content:downloads", "Downloads", "/content", "INTELLIGENCE", order=69, feature="content"),
    MenuItem("content:analysis", "Content Analysis", "/content", "INTELLIGENCE", order=70, feature="content"),

    MenuItem("hashtags", "Hashtags", "/hashtags", "INTELLIGENCE", icon="#️⃣", order=80, feature="hashtags"),
    MenuItem("hashtags:search", "Search Hashtags", "/hashtags", "INTELLIGENCE", order=81, feature="hashtags"),
    MenuItem("hashtags:info", "Hashtag Information", "/hashtags", "INTELLIGENCE", order=82, feature="hashtags"),
    MenuItem("hashtags:media", "Hashtag Media", "/hashtags", "INTELLIGENCE", order=83, feature="hashtags"),
    MenuItem("hashtags:recent", "Recent Posts", "/hashtags", "INTELLIGENCE", order=84, feature="hashtags"),
    MenuItem("hashtags:top", "Top Posts", "/hashtags", "INTELLIGENCE", order=85, feature="hashtags"),
    MenuItem("hashtags:analytics", "Hashtag Analytics", "/hashtags", "INTELLIGENCE", order=86, feature="hashtags"),

    MenuItem("locations", "Locations", "/locations", "INTELLIGENCE", icon="📍", order=90, feature="locations"),
    MenuItem("locations:search", "Search Locations", "/locations", "INTELLIGENCE", order=91, feature="locations"),
    MenuItem("locations:details", "Location Details", "/locations", "INTELLIGENCE", order=92, feature="locations"),
    MenuItem("locations:media", "Location Media", "/locations", "INTELLIGENCE", order=93, feature="locations"),
    MenuItem("locations:discovery", "Location Discovery", "/locations", "INTELLIGENCE", order=94, feature="locations"),

    MenuItem("analytics", "Analytics", "/analytics", "INTELLIGENCE", icon="📈", order=100, feature="analytics"),
    MenuItem("analytics:creator", "Creator Analytics", "/analytics", "INTELLIGENCE", order=101, feature="analytics"),
    MenuItem("analytics:post", "Post Analytics", "/analytics", "INTELLIGENCE", order=102, feature="analytics"),
    MenuItem("analytics:reel", "Reel Analytics", "/analytics", "INTELLIGENCE", order=103, feature="analytics"),
    MenuItem("analytics:story", "Story Analytics", "/analytics", "INTELLIGENCE", order=104, feature="analytics"),
    MenuItem("analytics:engagement", "Engagement", "/analytics", "INTELLIGENCE", order=105, feature="analytics"),
    MenuItem("analytics:audience", "Audience", "/analytics", "INTELLIGENCE", order=106, feature="analytics"),
    MenuItem("analytics:growth", "Growth", "/analytics", "INTELLIGENCE", order=107, feature="analytics"),
    MenuItem("analytics:insights", "Insights", "/analytics", "INTELLIGENCE", order=108, feature="analytics"),
    MenuItem("analytics:reports", "Reports", "/analytics", "INTELLIGENCE", order=109, feature="analytics"),

    MenuItem("collections", "Collections", "/collections", "INTELLIGENCE", icon="📚", order=120, feature="collections"),
    MenuItem("collections:mine", "My Collections", "/collections", "INTELLIGENCE", order=121, feature="collections"),
    MenuItem("collections:saved", "Saved Media", "/collections", "INTELLIGENCE", order=122, feature="collections"),
    MenuItem("collections:details", "Collection Details", "/collections", "INTELLIGENCE", order=123, feature="collections"),
    MenuItem("collections:media", "Collection Media", "/collections", "INTELLIGENCE", order=124, feature="collections"),

    MenuItem("notes", "Notes", "/notes", "INTELLIGENCE", icon="📝", order=130, feature="notes"),
    MenuItem("notes:mine", "My Notes", "/notes", "INTELLIGENCE", order=131, feature="notes"),
    MenuItem("notes:feed", "Notes Feed", "/notes", "INTELLIGENCE", order=132, feature="notes"),
    MenuItem("notes:management", "Note Management", "/notes", "INTELLIGENCE", order=133, feature="notes"),

    # -------------------------------------------------------------- engagement
    MenuItem("engagement", "Engagement", "/engagement", "ENGAGEMENT", icon="💬", order=140, feature="engagement"),
    MenuItem("engagement:comments", "Comments", "/engagement", "ENGAGEMENT", order=141, feature="engagement"),
    MenuItem("engagement:comment_search", "Comment Search", "/engagement", "ENGAGEMENT", order=142, feature="engagement"),
    MenuItem("engagement:likes", "Likes", "/engagement", "ENGAGEMENT", order=143, feature="engagement"),
    MenuItem("engagement:followers", "Followers", "/engagement", "ENGAGEMENT", order=144, feature="engagement"),
    MenuItem("engagement:following", "Following", "/engagement", "ENGAGEMENT", order=145, feature="engagement"),
    MenuItem("engagement:follow", "Follow / Unfollow", "/engagement", "ENGAGEMENT", order=146, feature="engagement"),
    MenuItem("engagement:block", "Block / Unblock", "/engagement", "ENGAGEMENT", order=147, feature="engagement"),
    MenuItem("engagement:restrict", "Restrict", "/engagement", "ENGAGEMENT", order=148, feature="engagement"),
    MenuItem("engagement:interactions", "Interactions", "/engagement", "ENGAGEMENT", order=149, feature="engagement"),

    MenuItem("direct", "Direct", "/direct", "ENGAGEMENT", icon="✉️", order=150, feature="direct"),
    MenuItem("direct:inbox", "Inbox", "/direct", "ENGAGEMENT", order=151, feature="direct"),
    MenuItem("direct:conversations", "Conversations", "/direct", "ENGAGEMENT", order=152, feature="direct"),
    MenuItem("direct:messages", "Messages", "/direct", "ENGAGEMENT", order=153, feature="direct"),
    MenuItem("direct:search", "Message Search", "/direct", "ENGAGEMENT", order=154, feature="direct"),
    MenuItem("direct:send", "Send Message", "/direct", "ENGAGEMENT", order=155, feature="direct"),
    MenuItem("direct:groups", "Group Threads", "/direct", "ENGAGEMENT", order=156, feature="direct"),
    MenuItem("direct:reactions", "Reactions", "/direct", "ENGAGEMENT", order=157, feature="direct"),
    MenuItem("direct:seen", "Read / Seen", "/direct", "ENGAGEMENT", order=158, feature="direct"),

    MenuItem("publishing", "Publishing", "/publishing", "ENGAGEMENT", icon="⬆️", order=160, feature="publishing"),
    MenuItem("publishing:photo", "Upload Photo", "/publishing", "ENGAGEMENT", order=161, feature="publishing"),
    MenuItem("publishing:video", "Upload Video", "/publishing", "ENGAGEMENT", order=162, feature="publishing"),
    MenuItem("publishing:reel", "Upload Reel", "/publishing", "ENGAGEMENT", order=163, feature="publishing"),
    MenuItem("publishing:story", "Upload Story", "/publishing", "ENGAGEMENT", order=164, feature="publishing"),
    MenuItem("publishing:album", "Upload Album", "/publishing", "ENGAGEMENT", order=165, feature="publishing"),
    MenuItem("publishing:igtv", "Upload IGTV", "/publishing", "ENGAGEMENT", order=166, feature="publishing"),
    MenuItem("publishing:builder", "Story Builder", "/publishing", "ENGAGEMENT", order=167, feature="publishing"),

    # --------------------------------------------------------------- accounts
    MenuItem("accounts", "Accounts", "/accounts", "ACCOUNTS", icon="📱", order=170, feature="accounts"),
    MenuItem("accounts:all", "All Accounts", "/accounts", "ACCOUNTS", order=171, feature="accounts"),
    MenuItem("accounts:add", "Add Account", "/accounts", "ACCOUNTS", order=172, feature="accounts"),
    MenuItem("accounts:profile", "Account Profile", "/accounts", "ACCOUNTS", order=173, feature="accounts"),
    MenuItem("accounts:info", "Account Information", "/accounts", "ACCOUNTS", order=174, feature="accounts"),
    MenuItem("accounts:health", "Account Health", "/accounts", "ACCOUNTS", order=175, feature="accounts"),
    MenuItem("accounts:activity", "Account Activity", "/accounts", "ACCOUNTS", order=176, feature="accounts"),
    MenuItem("accounts:followers", "Followers", "/accounts", "ACCOUNTS", order=177, feature="accounts"),
    MenuItem("accounts:following", "Following", "/accounts", "ACCOUNTS", order=178, feature="accounts"),
    MenuItem("accounts:notifications", "Notifications", "/accounts", "ACCOUNTS", order=179, feature="accounts"),

    MenuItem("sessions", "Sessions", "/sessions", "ACCOUNTS", icon="🔐", order=180, feature="sessions"),
    MenuItem("sessions:active", "Active Sessions", "/sessions", "ACCOUNTS", order=181, feature="sessions"),
    MenuItem("sessions:files", "Session Files", "/sessions", "ACCOUNTS", order=182, feature="sessions"),
    MenuItem("sessions:validate", "Session Validation", "/sessions", "ACCOUNTS", order=183, feature="sessions"),
    MenuItem("sessions:refresh", "Session Refresh", "/sessions", "ACCOUNTS", order=184, feature="sessions"),
    MenuItem("sessions:login", "Login", "/sessions", "ACCOUNTS", order=185, feature="sessions"),
    MenuItem("sessions:2fa", "2FA", "/sessions", "ACCOUNTS", order=186, feature="sessions"),
    MenuItem("sessions:challenge", "Challenge Status", "/sessions", "ACCOUNTS", order=187, feature="sessions"),
    MenuItem("sessions:health", "Session Health", "/sessions", "ACCOUNTS", order=188, feature="sessions"),

    # -------------------------------------------------------------- marketplace
    MenuItem("marketplace", "Marketplace", "/marketplace", "MARKETPLACE", icon="🛍️", order=190, feature="marketplace"),
    MenuItem("marketplace:find", "Find Creators", "/marketplace", "MARKETPLACE", order=191, feature="marketplace"),
    MenuItem("marketplace:hashtags", "Hashtags", "/marketplace", "MARKETPLACE", order=192, feature="marketplace"),
    MenuItem("marketplace:locations", "Locations", "/marketplace", "MARKETPLACE", order=193, feature="marketplace"),
    MenuItem("marketplace:all", "All Creators", "/marketplace", "MARKETPLACE", order=194, feature="marketplace"),
    MenuItem("marketplace:saved", "Saved", "/marketplace", "MARKETPLACE", order=195, feature="marketplace"),
    MenuItem("marketplace:lists", "Lists", "/marketplace", "MARKETPLACE", order=196, feature="marketplace"),
    MenuItem("marketplace:analysis", "Creator Analysis", "/marketplace", "MARKETPLACE", order=197, feature="marketplace"),

    # --------------------------------------------------------------- campaigns
    MenuItem("campaigns", "Campaigns", "/campaigns", "CAMPAIGNS", icon="🎯", order=200, feature="campaigns"),
    MenuItem("campaigns:all", "Campaigns", "/campaigns", "CAMPAIGNS", order=201, feature="campaigns"),
    MenuItem("campaigns:requests", "Requests", "/campaigns", "CAMPAIGNS", order=202, feature="campaigns"),
    MenuItem("campaigns:matching", "Matching", "/campaigns", "CAMPAIGNS", order=203, feature="campaigns"),
    MenuItem("campaigns:recommendations", "Recommendations", "/campaigns", "CAMPAIGNS", order=204, feature="campaigns"),

    # -------------------------------------------------------------------- data
    MenuItem("projects", "Projects", "/projects", "DATA", icon="📂", order=210, feature="projects"),
    MenuItem("projects:create", "New Project", "/projects", "DATA", order=211, feature="projects"),
    MenuItem("projects:urls", "Project URLs", "/projects", "DATA", order=212, feature="projects"),
    MenuItem("projects:runs", "Project Runs", "/projects", "DATA", order=213, feature="projects"),

    MenuItem("data", "Import / Export", "/data", "DATA", icon="📥", order=220, feature="data"),
    MenuItem("data:import", "Import", "/data", "DATA", order=221, feature="data"),
    MenuItem("data:export", "Export", "/data", "DATA", order=222, feature="data"),
    MenuItem("data:bulk", "Bulk Operations", "/data", "DATA", order=223, feature="data"),
    MenuItem("data:downloads", "Downloads", "/data", "DATA", order=224, feature="data"),
    MenuItem("data:quality", "Data Quality", "/data", "DATA", order=225, feature="data"),
    MenuItem("data:dedupe", "Deduplication", "/data", "DATA", order=226, feature="data"),
    MenuItem("data:refresh", "Data Refresh", "/data", "DATA", order=227, feature="data"),

    MenuItem("database", "Database", "/database", "DATA", icon="🗄️", order=230, feature="database"),
    MenuItem("database:local", "Local PostgreSQL", "/database", "DATA", order=231, feature="database"),
    MenuItem("database:remote", "SQL Server", "/database", "DATA", order=232, feature="database"),
    MenuItem("database:search", "Profile Search", "/database", "DATA", order=233, feature="database"),
    MenuItem("database:schema", "Schema Explorer", "/database", "DATA", order=234, feature="database"),

    MenuItem("storage", "Storage", "/storage", "DATA", icon="☁️", order=240, feature="storage"),
    MenuItem("storage:status", "Storage Status", "/storage", "DATA", order=241, feature="storage"),
    MenuItem("storage:keys", "Keys", "/storage", "DATA", order=242, feature="storage"),
    MenuItem("storage:upload", "Upload", "/storage", "DATA", order=243, feature="storage"),
    MenuItem("storage:download", "Download", "/storage", "DATA", order=244, feature="storage"),

    # -------------------------------------------------------------- automation
    MenuItem("automation", "Automation", "/monitoring", "AUTOMATION", icon="⚙️", order=300, feature="automation"),
    MenuItem("automation:jobs", "Jobs", "/monitoring", "AUTOMATION", order=301, feature="automation"),
    MenuItem("automation:scheduled", "Scheduled Jobs", "/monitoring", "AUTOMATION", order=302, feature="automation"),
    MenuItem("automation:workers", "Workers", "/monitoring", "AUTOMATION", order=303, feature="automation"),
    MenuItem("automation:queues", "Queues", "/monitoring", "AUTOMATION", order=304, feature="automation"),
    MenuItem("automation:monitoring", "Monitoring", "/monitoring", "AUTOMATION", order=305, feature="automation"),
    MenuItem("automation:history", "Job History", "/monitoring", "AUTOMATION", order=306, feature="automation"),

    MenuItem("jobs", "Jobs", "/jobs", "AUTOMATION", icon="⚡", order=310, feature="jobs"),
    MenuItem("jobs:queued", "Queued", "/jobs", "AUTOMATION", order=311, feature="jobs"),
    MenuItem("jobs:running", "Running", "/jobs", "AUTOMATION", order=312, feature="jobs"),
    MenuItem("jobs:completed", "Completed", "/jobs", "AUTOMATION", order=313, feature="jobs"),
    MenuItem("jobs:failed", "Failed", "/jobs", "AUTOMATION", order=314, feature="jobs"),

    MenuItem("monitoring", "Monitoring", "/monitoring", "AUTOMATION", icon="📊", order=320, feature="monitoring"),
    MenuItem("monitoring:jobs", "Jobs Overview", "/monitoring", "AUTOMATION", order=321, feature="monitoring"),
    MenuItem("monitoring:history", "Job History", "/monitoring", "AUTOMATION", order=322, feature="monitoring"),

    # ------------------------------------------------------------------ system
    MenuItem("settings", "Settings", "/settings", "SYSTEM", icon="⚙️", order=400, feature="settings"),
    MenuItem("settings:general", "General", "/settings", "SYSTEM", order=401, feature="settings"),
    MenuItem("settings:instagram", "Instagram Accounts", "/settings", "SYSTEM", order=402, feature="settings"),
    MenuItem("settings:sessions", "Sessions", "/settings", "SYSTEM", order=403, feature="settings"),
    MenuItem("settings:proxy", "Proxy", "/settings", "SYSTEM", order=404, feature="settings"),
    MenuItem("settings:requests", "Request Settings", "/settings", "SYSTEM", order=405, feature="settings"),
    MenuItem("settings:notifications", "Notifications", "/settings", "SYSTEM", order=406, feature="settings"),
    MenuItem("settings:storage", "Storage", "/settings", "SYSTEM", order=407, feature="settings"),
    MenuItem("settings:api", "API", "/settings", "SYSTEM", order=408, feature="settings"),
    MenuItem("settings:workers", "Workers", "/settings", "SYSTEM", order=409, feature="settings"),
    MenuItem("settings:system", "System", "/settings", "SYSTEM", order=410, feature="settings"),

    MenuItem("admin", "Administration", "/admin", "SYSTEM", icon="🛠️", order=420, feature="admin"),
    MenuItem("admin:features", "Feature Controls", "/admin", "SYSTEM", order=421, feature="admin"),
    MenuItem("admin:users", "Users", "/admin", "SYSTEM", order=422, feature="admin"),
    MenuItem("admin:audit", "Audit Log", "/admin", "SYSTEM", order=423, feature="admin"),

    MenuItem("tracking", "Tracking", "/tracking", "SYSTEM", icon="🛰️", order=430, feature="tracking"),
    MenuItem("tracking:traffic", "API Traffic", "/tracking", "SYSTEM", order=431, feature="tracking"),
    MenuItem("tracking:connections", "Connections", "/tracking", "SYSTEM", order=432, feature="tracking"),
]


MENU_GROUPS: list[str] = [
    "MAIN",
    "INTELLIGENCE",
    "ENGAGEMENT",
    "ACCOUNTS",
    "MARKETPLACE",
    "CAMPAIGNS",
    "DATA",
    "AUTOMATION",
    "SYSTEM",
]