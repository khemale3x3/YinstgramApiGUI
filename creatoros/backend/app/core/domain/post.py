from __future__ import annotations
from pydantic import BaseModel


class CreatorPost(BaseModel):
    """A single Instagram media item (post / reel / album)."""

    pk: str
    shortcode: str
    media_type: str
    taken_at: str | None = None
    caption: str = ""
    likes: int = 0
    comments: int = 0
    plays: int = 0
    views: int = 0
    thumbnail_url: str | None = None
    video_url: str | None = None
    location: str | None = None