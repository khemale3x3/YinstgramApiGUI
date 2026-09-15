"""Campaign routes — CRUD, creator matching and outreach requests.

Feature-gated on `campaigns`; matching runs against the saved profile store.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.services.campaign_service import CampaignService


def build_router(campaign_service: CampaignService, require_feature) -> APIRouter:
    router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])
    gate = require_feature("campaigns")

    @router.get("")
    def list_campaigns(_: dict = Depends(gate)) -> dict:
        return {"campaigns": campaign_service.list()}

    @router.post("")
    def create_campaign(
        payload: dict, _: dict = Depends(gate)
    ) -> dict:
        campaign = campaign_service.create(
            name=str(payload.get("name") or "").strip(),
            budget_min=int(payload.get("budget_min") or 0),
            budget_max=int(payload.get("budget_max") or 0),
            target_count=int(payload.get("target_count") or 10),
            location=str(payload.get("location") or "").strip(),
            audience=str(payload.get("audience") or "").strip(),
            min_engagement=float(payload.get("min_engagement") or 0),
            notes=str(payload.get("notes") or "").strip(),
        )
        return {"campaign": campaign.__dict__}

    @router.get("/stats")
    def stats(_: dict = Depends(gate)) -> dict:
        return campaign_service.stats()

    @router.get("/{campaign_id}")
    def get_campaign(campaign_id: str, _: dict = Depends(gate)) -> dict:
        campaign = campaign_service.get(campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"campaign": campaign}

    @router.patch("/{campaign_id}")
    def update_campaign(campaign_id: str, payload: dict, _: dict = Depends(gate)) -> dict:
        campaign = campaign_service.update(campaign_id, **payload)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"campaign": campaign.__dict__}

    @router.delete("/{campaign_id}")
    def delete_campaign(campaign_id: str, _: dict = Depends(gate)) -> dict:
        if not campaign_service.delete(campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"deleted": True}

    @router.post("/{campaign_id}/match")
    def match(campaign_id: str, _: dict = Depends(gate)) -> dict:
        try:
            return campaign_service.match(campaign_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.post("/{campaign_id}/request")
    def send_request(campaign_id: str, payload: dict, _: dict = Depends(gate)) -> dict:
        if campaign_service.get(campaign_id) is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        username = str(payload.get("username") or "").strip()
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        request = campaign_service.request(
            campaign_id, username, message=str(payload.get("message") or "")
        )
        return {"request": request.__dict__}

    @router.patch("/{campaign_id}/requests/{username}")
    def update_request(campaign_id: str, username: str, payload: dict, _: dict = Depends(gate)) -> dict:
        status = str(payload.get("status") or "")
        if not campaign_service.set_request_status(campaign_id, username, status):
            raise HTTPException(status_code=400, detail=f"Invalid request status '{status}'")
        return {"updated": True, "status": status}

    @router.patch("/{campaign_id}/creators/{username}")
    def update_creator(campaign_id: str, username: str, payload: dict, _: dict = Depends(gate)) -> dict:
        status = str(payload.get("status") or "")
        if not campaign_service.set_creator_status(campaign_id, username, status):
            raise HTTPException(status_code=400, detail=f"Invalid creator status '{status}'")
        return {"updated": True, "status": status}

    # ------------------------------------------------------------- approval workflow
    @router.post("/{campaign_id}/approval/request")
    def request_approval(campaign_id: str, _: dict = Depends(gate)) -> dict:
        ok = campaign_service.request_approval(campaign_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Cannot request approval")
        return {"approved": True}

    @router.post("/{campaign_id}/approval/approve")
    def approve_campaign(campaign_id: str, _: dict = Depends(gate)) -> dict:
        ok = campaign_service.approve_campaign(campaign_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Cannot approve campaign")
        return {"approved": True}

    @router.post("/{campaign_id}/approval/reject")
    def reject_campaign(campaign_id: str, _: dict = Depends(gate)) -> dict:
        ok = campaign_service.reject_campaign(campaign_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Cannot reject campaign")
        return {"rejected": True}

    @router.post("/{campaign_id}/approval/request-changes")
    def request_changes(campaign_id: str, payload: dict, _: dict = Depends(gate)) -> dict:
        comment = str(payload.get("comment") or "")
        ok = campaign_service.request_changes(campaign_id, comment)
        if not ok:
            raise HTTPException(status_code=400, detail="Cannot request changes")
        return {"requested_changes": True}

    return router
