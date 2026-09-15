from __future__ import annotations
from pydantic import BaseModel


class Creator(BaseModel):
    """Instagram creator profile entity."""

    pk: str
    username: str
    full_name: str
    biography: str = ""
    external_url: str | None = None
    followers: int = 0
    following: int = 0
    media_count: int = 0
    is_private: bool = False
    is_verified: bool = False
    category: str = ""
    # relationship tracking
    relationship_status: str = "new"
    first_discovered: str | None = None
    first_contacted: str | None = None
    last_contacted: str | None = None
    last_response: str | None = None
    contact_count: int = 0
    campaign_count: int = 0
    successful_campaigns: int = 0
    current_campaign: str | None = None
    relationship_owner: str = "admin"
    tags: str = ""
    preferred_collaboration_type: str = ""
    content_categories: str = ""
    historical_performance: str = ""
    last_known_availability: str = "unknown"
    relationship_health_score: int = 0
    data_freshness: str = "never collected"
    # collaboration availability
    availability_status: str = "unknown"
    available_from: str | None = None
    available_until: str | None = None
    collaboration_types: str = ""
    preferred_categories: str = ""
    minimum_budget: int = 0