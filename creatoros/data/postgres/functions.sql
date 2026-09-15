-- CreatorOS SQL functions (read path / aggregate helpers).

SET search_path = creatoros;

CREATE OR REPLACE FUNCTION count_profiles() RETURNS BIGINT
LANGUAGE sql
AS $$
    SELECT COUNT(*) FROM creatoros.profiles;
$$;

CREATE OR REPLACE FUNCTION sum_media_count() RETURNS BIGINT
LANGUAGE sql
AS $$
    SELECT COALESCE(SUM(media_count), 0) FROM creatoros.profiles;
$$;

CREATE OR REPLACE FUNCTION top_profiles(p_limit INTEGER)
RETURNS TABLE (
    username        TEXT, url TEXT, followers INTEGER, following INTEGER,
    media_count     INTEGER, is_private BOOLEAN, is_verified BOOLEAN,
    full_name TEXT, biography TEXT, category TEXT, profile_pic_url TEXT,
    scraped_at TEXT, profile_info TEXT, post_info TEXT
)
LANGUAGE sql
AS $$
    SELECT username, url, followers, following, media_count, is_private,
           is_verified, full_name, biography, category, profile_pic_url,
           scraped_at, profile_info, post_info
    FROM creatoros.profiles
    ORDER BY followers DESC
    LIMIT p_limit;
$$;

CREATE OR REPLACE FUNCTION search_profiles(p_query TEXT, p_limit INTEGER DEFAULT 20)
RETURNS TABLE (
    username        TEXT, url TEXT, followers INTEGER, following INTEGER,
    media_count     INTEGER, is_private BOOLEAN, is_verified BOOLEAN,
    full_name TEXT, biography TEXT, category TEXT, profile_pic_url TEXT,
    scraped_at TEXT, profile_info TEXT, post_info TEXT
)
LANGUAGE sql
AS $$
    SELECT username, url, followers, following, media_count, is_private,
           is_verified, full_name, biography, category, profile_pic_url,
           scraped_at, profile_info, post_info
    FROM creatoros.profiles
    WHERE username ILIKE '%' || p_query || '%'
       OR full_name  ILIKE '%' || p_query || '%'
       OR biography  ILIKE '%' || p_query || '%'
       OR category   ILIKE '%' || p_query || '%'
    ORDER BY scraped_at DESC
    LIMIT p_limit;
$$;