"""Tracking routes — every API call + connection for audit/insight.

Backed by the `api_traffic` and `connection_logs` tables; admin-only
(feature `tracking`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.services.admin_service import AdminService


def build_router(admin_service: AdminService, require_admin, require_feature) -> APIRouter:
    router = APIRouter(prefix="/api/tracking", tags=["Tracking"])
    gate = require_feature("tracking")

    @router.get("/traffic")
    def traffic(limit: int = Query(default=200, ge=1, le=1000), _: dict = Depends(gate)) -> dict:
        return {"entries": admin_service.traffic(limit=limit)}

    @router.get("/connections")
    def connections(limit: int = Query(default=100, ge=1, le=500), _: dict = Depends(gate)) -> dict:
        return {"entries": admin_service.connections(limit=limit)}

    @router.get("/stats")
    def stats(_: dict = Depends(gate)) -> dict:
        return admin_service.traffic_stats()

    return router