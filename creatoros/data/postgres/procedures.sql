-- CreatorOS stored procedures (write path).
-- Called by the port adapters so all writes funnel through the same logic.

SET search_path = creatoros;

-- Upsert a scraped profile (used by the scrape/analyze pipeline).
CREATE OR REPLACE PROCEDURE upsert_profile(
    p_username        TEXT,
    p_url             TEXT,
    p_profile_info    TEXT,
    p_post_info       TEXT,
    p_followers       INTEGER,
    p_following       INTEGER,
    p_media_count     INTEGER,
    p_is_private      BOOLEAN,
    p_is_verified     BOOLEAN,
    p_full_name       TEXT,
    p_biography       TEXT,
    p_category        TEXT,
    p_profile_pic_url TEXT,
    p_scraped_at      TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO creatoros.profiles (
        username, url, profile_info, post_info, followers, following,
        media_count, is_private, is_verified, full_name, biography,
        category, profile_pic_url, scraped_at
    ) VALUES (
        p_username, p_url, p_profile_info, p_post_info, p_followers, p_following,
        p_media_count, p_is_private, p_is_verified, p_full_name, p_biography,
        p_category, p_profile_pic_url, p_scraped_at
    )
    ON CONFLICT (username) DO UPDATE SET
        url             = EXCLUDED.url,
        profile_info    = EXCLUDED.profile_info,
        post_info       = EXCLUDED.post_info,
        followers       = EXCLUDED.followers,
        following       = EXCLUDED.following,
        media_count     = EXCLUDED.media_count,
        is_private      = EXCLUDED.is_private,
        is_verified     = EXCLUDED.is_verified,
        full_name       = EXCLUDED.full_name,
        biography       = EXCLUDED.biography,
        category        = EXCLUDED.category,
        profile_pic_url = EXCLUDED.profile_pic_url,
        scraped_at      = EXCLUDED.scraped_at;
END;
$$;

-- Append an audit-log entry.
CREATE OR REPLACE PROCEDURE record_audit(
    p_id TEXT, p_user TEXT, p_action TEXT, p_target TEXT, p_detail TEXT, p_created_at TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO creatoros.audit_logs (id, "user", action, target, detail, created_at)
    VALUES (p_id, p_user, p_action, p_target, p_detail, p_created_at);
END;
$$;