"""Campaigns use case: CRUD + creator matching on top of the profile store."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.domain.campaign import Campaign, CampaignCreator, CampaignRequest
from app.core.ports.campaign import CampaignStorePort

VALID_STATUSES = ("draft", "pending_review", "approved", "rejected", "changes_requested", "launched", "completed", "cancelled")
_MATCH_STATUSES = ("matched", "shortlisted", "added", "accepted", "requested", "declined")
_REQUEST_STATUSES = ("pending", "sent", "accepted", "declined")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CampaignService:
    """Use case: campaigns, creator matching and outreach requests."""

    def __init__(self, store: CampaignStorePort, db, pool_size: int = 800):
        self._store = store
        self._db = db
        self.pool_size = int(pool_size)

    # ------------------------------------------------------------------ CRUD
    def create(self, name: str, budget_min: int = 0, budget_max: int = 0,
               target_count: int = 10, location: str = "", audience: str = "",
               min_engagement: float = 0.0, notes: str = "") -> Campaign:
        c = Campaign(
            id=f"cmp_{uuid.uuid4().hex[:12]}",
            name=(name or "Untitled campaign").strip(),
            budget_min=int(budget_min or 0),
            budget_max=int(budget_max or 0),
            target_count=max(1, int(target_count or 1)),
            location=(location or "").strip(),
            audience=(audience or "").strip(),
            min_engagement=float(min_engagement or 0),
            notes=(notes or "").strip(),
            created_at=_now(),
            updated_at=_now(),
        )
        return self._store.create_campaign(c)

    def update(self, campaign_id: str, **fields) -> Campaign | None:
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return None
        for key, value in fields.items():
            if key == "min_engagement":
                value = float(value or 0)
            elif key == "target_count":
                value = max(1, int(value or 1))
            elif key == "status" and value not in VALID_STATUSES:
                continue
            if key in ("name", "budget_min", "budget_max", "target_count", "location",
                       "audience", "min_engagement", "status", "notes"):
                setattr(c, key, value)
        c.updated_at = _now()
        return self._store.update_campaign(c)

    def get(self, campaign_id: str) -> dict | None:
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return None
        data = self._to_dict(c)
        data["creators"] = [cc.__dict__ for cc in self._store.list_creators(campaign_id)]
        data["requests"] = [r.__dict__ for r in self._store.list_requests(campaign_id)]
        return data

    def list(self) -> list[dict]:
        campaigns = self._store.list_campaigns()
        out = []
        for c in campaigns:
            data = self._to_dict(c)
            data["matched"] = len(self._store.list_creators(c.id))
            out.append(data)
        return out

    def delete(self, campaign_id: str) -> bool:
        return self._store.delete_campaign(campaign_id)

    def stats(self) -> dict:
        return self._store.campaign_stats()

    # ------------------------------------------------------------- matching
    def match(self, campaign_id: str, limit: int | None = None) -> dict:
        """Score saved profiles against the campaign brief and persist matches."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            raise ValueError(f"Campaign {campaign_id!r} not found")

        limit = limit or c.target_count
        pool = self._collect_pool(c)
        if not pool:
            self._store.replace_creators(campaign_id, [])
            return {"matched": 0, "message": "No saved creators available to match against"}

        scored = [self._score(c, p) for p in pool]
        scored = [s for s in scored if s["score"] > 0]
        scored.sort(key=lambda s: (-s["score"], -s["followers"]))
        scored = scored[:limit]

        rows = [
            CampaignCreator(
                id=f"cm_{uuid.uuid4().hex[:12]}",
                campaign_id=campaign_id,
                creator_username=s["username"],
                score=round(s["score"], 1),
                match_pct=round(s["score"], 1),
                rank=idx + 1,
                status="matched",
                followers=s["followers"],
                full_name=s["full_name"],
                category=s["category"],
                location=s["location"],
                biography=(s["biography"] or "")[:300],
                engagement=round(s["engagement"], 3),
                created_at=_now(),
            )
            for idx, s in enumerate(scored)
        ]
        self._store.replace_creators(campaign_id, rows)

        matched = self._store.list_creators(campaign_id)
        if c.status == "draft" and matched:
            self.update(campaign_id, status="matched")
        return {"matched": len(matched), "campaign_id": campaign_id,
                "creators": [cc.__dict__ for cc in matched]}

    def _collect_pool(self, c: Campaign) -> list[dict]:
        pool: dict[str, dict] = {}
        if self._db is not None:
            try:
                for p in self._db.top(self.pool_size) or []:
                    pool[p["username"]] = p
            except Exception:
                pass
            if c.audience:
                terms = [t.strip() for t in c.audience.replace(",", " ").split() if t.strip()][:5]
                for term in terms:
                    try:
                        for p in self._db.search(term, 100) or []:
                            pool[p["username"]] = p
                    except Exception:
                        pass
            if c.location:
                try:
                    for p in self._db.search(c.location, 100) or []:
                        pool[p["username"]] = p
                except Exception:
                    pass
        return list(pool.values())

    def _score(self, c: Campaign, p: dict) -> dict:
        followers = int(p.get("followers") or 0)
        media = int(p.get("media_count") or 0)
        bio = f"{p.get('biography') or ''} {p.get('category') or ''} {p.get('full_name') or ''}".lower()

        score = 5.0  # baseline for having a saved profile
        if p.get("is_private"):
            score -= 20
        if p.get("is_verified"):
            score += 3

        if followers > 0:
            engagement = min(media / followers, 1.0)
        else:
            engagement = 0.0

        if c.min_engagement > 0:
            if engagement >= c.min_engagement:
                score += 25
            elif engagement >= c.min_engagement * 0.5:
                score += 10
            else:
                score -= 15

        if c.budget_min > 0:
            if budget_floor := int(c.budget_min or 0):
                if followers >= budget_floor * 3:
                    score += 15
                elif followers >= budget_floor:
                    score += 8

        if c.audience:
            keywords = [t.lower().strip() for t in c.audience.replace(",", " ").split() if t.strip()]
            hits = sum(1 for kw in keywords if kw in bio)
            score += min(hits, 5) * 6

        if c.location:
            location = f"{p.get('location') or ''} {bio}".lower()
            for token in c.location.replace(",", " ").split():
                if token.lower().strip() and token.lower().strip() in location:
                    score += 8
                    break

        if p.get("category"):
            score += 2

        score = max(score, 0.0)
        return {
            "username": p["username"], "followers": followers,
            "full_name": p.get("full_name") or "", "category": p.get("category") or "",
            "location": p.get("location") or "", "biography": p.get("biography") or "",
            "engagement": round(engagement, 4), "score": round(min(score, 100), 1),
        }

    # ------------------------------------------------------------- outreach
    def request(self, campaign_id: str, username: str, message: str = "") -> CampaignRequest:
        req = CampaignRequest(
            id=f"req_{uuid.uuid4().hex[:12]}",
            campaign_id=campaign_id,
            creator_username=username.strip(),
            message=(message or "").strip(),
            created_at=_now(),
        )
        self._store.add_request(req)
        self._store.set_creator_status(campaign_id, username, "requested")
        return req

    def set_request_status(self, campaign_id: str, username: str, status: str) -> bool:
        if status not in _REQUEST_STATUSES:
            return False
        ok = self._store.set_request_status(campaign_id, username, status)
        mapping = {"accepted": "accepted", "declined": "declined"}
        if ok and status in mapping:
            self._store.set_creator_status(campaign_id, username, mapping[status])
        return ok

    def set_creator_status(self, campaign_id: str, username: str, status: str) -> bool:
        if status not in _MATCH_STATUSES:
            return False
        return self._store.set_creator_status(campaign_id, username, status)

    # ------------------------------------------------------------- approval workflow
    def request_approval(self, campaign_id: str) -> bool:
        """Request campaign approval. Moves status to pending_review."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id, status="pending_review",
            requested_by="admin", requested_at=now)
        return True

    def approve_campaign(self, campaign_id: str) -> bool:
        """Approve a campaign. Moves status to approved."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id, status="approved",
            reviewed_by="admin", reviewed_at=now, decision="approved")
        return True

    def reject_campaign(self, campaign_id: str) -> bool:
        """Reject a campaign. Moves status to rejected."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id, status="rejected",
            reviewed_by="admin", reviewed_at=now, decision="rejected")
        return True

    def request_changes(self, campaign_id: str, comment: str) -> bool:
        """Request changes to the campaign."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id, status="changes_requested",
            reviewed_by="admin", reviewed_at=now, comment=comment)
        return True

    # --------------------------------------------------------------- helpers

    # ------------------------------------------------------------- budget ledger
    def set_budget(self, campaign_id: str, total_budget: int, currency: str = "USD") -> bool:
        """Set the total budget for a campaign."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        c.total_budget = total_budget
        c.budget_currency = currency
        c.remaining = total_budget - c.committed
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id)
        return True

    def commit_budget(self, campaign_id: str, amount: int, category: str = "creator",
                       creator_username: str = "", notes: str = "") -> bool:
        """Commit budget allocation."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        c.committed += amount
        c.remaining = c.total_budget - c.committed
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.set_budget(campaign_id, c.total_budget, c.budget_currency)
        self._store.update_campaign(campaign_id)
        # Add budget event
        self._store.add_budget_event(campaign_id, amount, category, creator_username, "committed", notes)
        return True

    def record_spend(self, campaign_id: str, amount: int, creator_username: str = "",
                      notes: str = "") -> bool:
        """Record a budget spend."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return False
        c.spent += amount
        c.remaining = c.total_budget - c.spent
        now = __import__("datetime").datetime.now(timezone.utc).isoformat()
        self._store.update_campaign(campaign_id)
        # Add budget event
        self._store.add_budget_event(campaign_id, amount, "spend", creator_username, "spent", notes)
        return True

    def get_budget_summary(self, campaign_id: str) -> dict:
        """Get budget summary for a campaign."""
        c = self._store.get_campaign(campaign_id)
        if c is None:
            return {"total": 0, "allocated": 0, "committed": 0, "spent": 0, "remaining": 0, "currency": "USD"}
        summary = {
            "total": c.total_budget,
            "allocated": c.allocated,
            "committed": c.committed,
            "spent": c.spent,
            "remaining": c.remaining,
            "currency": c.budget_currency,
        }
        # Also check database for events
        summary.update(self._store.get_budget_summary(campaign_id))
        return summary


    @staticmethod
    def _to_dict(c: Campaign) -> dict:
        return c.__dict__.copy()