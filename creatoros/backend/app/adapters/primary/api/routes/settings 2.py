from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from app.adapters.primary.api.schemas import SettingsUpdateRequest
from app.core.services.settings_service import SettingsService


def build_router(settings_service: SettingsService, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["Settings"], dependencies=dependencies)

    @router.get("")
    def get_settings(_: dict = Depends(require_admin)):
        return settings_service.to_dict(include_secrets=False)

    @router.put("")
    def update_settings(payload: SettingsUpdateRequest, _: dict = Depends(require_admin)):
        patch = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not patch:
            return settings_service.to_dict(include_secrets=False)
        try:
            return settings_service.update(patch)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router