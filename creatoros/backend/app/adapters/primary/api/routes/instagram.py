from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import requests
from app.core.config import settings


class InstagramActionRequest(BaseModel):
    action: str = Field(pattern="^(publish_photo|publish_video|publish_album|comment|comments|direct_send|hashtag_info|hashtag_recent|hashtag_top|insights)$")
    payload: dict = {}


def build_router(instagram_factory, sessions, operation_store, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/instagram", tags=["Instagram"], dependencies=dependencies)

    @router.post("/actions")
    def action(request: InstagramActionRequest, _: dict = Depends(require_admin)):
        if request.action == "insights":
            if not settings.instagram_graph_business_account_id or not settings.instagram_graph_access_token:
                accounts = sessions.list_accounts()
                if not accounts:
                    raise HTTPException(status_code=400, detail="Configure an Instagram account session or Instagram Graph API credentials in Settings")
                try:
                    result = instagram_factory(sessions.load(accounts[0])).execute_action("insights", request.payload)
                    operation_store.record_operation(request.action, request.payload, result)
                    return result
                except Exception as exc:
                    operation_store.record_operation(request.action, request.payload, status="failed", error=str(exc))
                    raise HTTPException(status_code=400, detail="Instagram Insights requires a Business account and a valid authenticated session") from exc
            params = {"access_token": settings.instagram_graph_access_token, "metric": request.payload.get("metric", "impressions,reach,follower_count"), "period": request.payload.get("period", "day")}
            url = f"https://graph.facebook.com/{settings.instagram_graph_api_version}/{settings.instagram_graph_business_account_id}/insights"
            try:
                response = requests.get(url, params=params, timeout=20)
                response.raise_for_status()
                result = {"action": request.action, "data": response.json().get("data", [])}
                operation_store.record_operation(request.action, {"metric": params["metric"], "period": params["period"]}, result)
                return result
            except Exception as exc:
                operation_store.record_operation(request.action, request.payload, status="failed", error=str(exc))
                raise HTTPException(status_code=400, detail="Instagram Graph API Insights request failed; verify account, permissions, and token") from exc
        accounts = sessions.list_accounts()
        if not accounts:
            raise HTTPException(status_code=400, detail="No authenticated Instagram account session is configured")
        account = accounts[0]
        client = instagram_factory(sessions.load(account))
        try:
            result = client.execute_action(request.action, request.payload)
            operation_store.record_operation(request.action, request.payload, result)
            return result
        except Exception as exc:
            operation_store.record_operation(request.action, request.payload, status="failed", error=str(exc))
            raise HTTPException(status_code=400, detail="Instagram operation failed; check the account session and provider response") from exc

    return router