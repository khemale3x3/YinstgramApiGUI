"""Campaign + campaign-creator match domain entities.

A campaign encodes the targeting brief (budget, audience, location,
engagement floor); matching scores saved creators (from the profiles store)
against those criteria and persists CampaignCreator rows so the UI can rank,
approve and reach out.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Campaign:
    id: str
    name: str
    budget_min: int = 0
    budget_max: int = 0
    target_count: int = 10
    location: str = ""
    audience: str = ""
    min_engagement: float = 0.0
    status: str = "draft"  # draft | pending_review | approved | rejected | changes_requested | launched | completed | archived
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    # approval metadata
    requested_by: str = ""
    requested_at: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""
    decision: str = ""
    comment: str = ""
    # budget ledger
    total_budget: int = 0
    allocated: int = 0
    committed: int = 0
    spent: int = 0
    remaining: int = 0
    budget_currency: str = "USD"


@dataclass
class CampaignCreator:
    id: str
    campaign_id: str
    creator_username: str
    score: float = 0.0
    match_pct: float = 0.0
    rank: int = 0
    status: str = "matched"  # matched | shortlisted | added | accepted | requested | declined
    followers: int = 0
    full_name: str = ""
    category: str = ""
    location: str = ""
    biography: str = ""
    engagement: float = 0.0
    created_at: str = ""


@dataclass
class CampaignRequest:
    id: str
    campaign_id: str
    creator_username: str
    status: str = "pending"  # pending | sent | accepted | declined
    message: str = ""
    created_at: str = field(default="")