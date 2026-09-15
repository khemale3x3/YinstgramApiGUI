"""Admin routes — feature flags, menu tree and audit trail.

Users / roles / permissions and invitation flows land in a later pass; the
*foundation* (RBAC tables already present in creatoros.db, backend-enforced
feature gates) is live today, so the admin can flip a feature and the menu
tree + every gated route react immediately.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.primary.api.schemas import FeatureUpdateRequest, UserUpdateRequest
from app.core.services.admin_service import AdminService


def build_router(admin_service: AdminService, require_admin, require_feature) -> APIRouter:
    router = APIRouter(prefix="/api/admin", tags=["Admin"])
    admin_gate = require_feature("admin")

    @router.get("/features")
    def list_features(_: dict = Depends(admin_gate)) -> list[dict]:
        return admin_service.features()

    @router.put("/features/{key}")
    def set_feature(key: str, payload: FeatureUpdateRequest, identity: dict = Depends(admin_gate)) -> dict:
        return admin_service.set_feature(key, payload.enabled, actor=identity.get("email", ""))

    @router.get("/menus")
    def menus(_: dict = Depends(admin_gate)) -> dict:
        return admin_service.menus()

    @router.get("/audit")
    def audit_logs(limit: int = Query(default=50, ge=1, le=500), _: dict = Depends(admin_gate)):
        return {"entries": admin_service.audit_logs(limit=limit)}

    @router.get("/users")
    def users(_: dict = Depends(admin_gate)):
        return {"users": admin_service.list_users()}

    @router.put("/users/{user_id}")
    def update_user(user_id: str, payload: UserUpdateRequest, identity: dict = Depends(admin_gate)):
        updated = admin_service.update_user(
            user_id,
            role=payload.role,
            status=payload.status,
            name=payload.name,
            username=payload.username,
            actor=identity.get("email", ""),
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="user not found")
        return {"user": updated}

    return router