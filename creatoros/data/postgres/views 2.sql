-- CreatorOS read-model views.

SET search_path = creatoros;

-- Jobs grouped by status (dashboard chips).
CREATE OR REPLACE VIEW v_jobs_by_status AS
SELECT status, COUNT(*)::BIGINT AS cnt
FROM creatoros.jobs
GROUP BY status;

-- Dashboard one-number stats.
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    (SELECT COUNT(*)::BIGINT FROM creatoros.profiles)        AS creators,
    (SELECT COALESCE(SUM(media_count), 0)::BIGINT FROM creatoros.profiles) AS posts_analyzed,
    (SELECT COALESCE(COUNT(*), 0) FROM creatoros.jobs WHERE status = 'running')::BIGINT AS jobs_running;

-- Audit trail, newest first.
CREATE OR REPLACE VIEW v_recent_activity AS
SELECT id, "user", action, target, detail, created_at
FROM creatoros.audit_logs
ORDER BY created_at DESC
LIMIT 50;

-- Profiles ranked by followers.
CREATE OR REPLACE VIEW v_profiles_by_followers AS
SELECT username, url, followers, following, media_count, is_private,
       is_verified, full_name, biography, category, profile_pic_url, scraped_at
FROM creatoros.profiles
ORDER BY followers DESC;

-- Marketplace funnel: richest categories by creator count + avg audience.
CREATE OR REPLACE VIEW v_profiles_by_category AS
SELECT COALESCE(NULLIF(category, ''), 'uncategorized') AS category,
       COUNT(*)::BIGINT AS creators,
       COALESCE(ROUND(AVG(followers)), 0)::BIGINT AS avg_followers
FROM creatoros.profiles
GROUP BY 1
ORDER BY creators DESC;

-- Content-ratio read model per creator (media per 1k followers as an honest,
-- stored-data-only proxy for engagement benchmarking).
CREATE OR REPLACE VIEW v_engagement_insights AS
SELECT username,
       followers,
       following,
       media_count,
       CASE WHEN followers > 0
            THEN ROUND((media_count::NUMERIC / GREATEST(followers, 1) * 1000), 2)
            ELSE 0 END AS content_per_1k_followers
FROM creatoros.profiles
ORDER BY content_per_1k_followers DESC;