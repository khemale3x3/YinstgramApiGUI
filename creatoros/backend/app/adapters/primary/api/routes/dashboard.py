"""Dashboard routes — the control-center aggregates for the frontend home page."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.services.dashboard_service import DashboardService


def build_router(dashboard: DashboardService, require_admin, require_feature) -> APIRouter:
    router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
    gate = require_feature("dashboard")

    @router.get("")
    def snapshot(_: dict = Depends(gate)) -> dict:
        return dashboard.snapshot()

    return router