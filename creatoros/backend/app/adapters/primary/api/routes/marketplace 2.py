"""Marketplace routes — category browsing, discovery and saving creators.

Feature-gated on `marketplace`. Discovery calls a live Instagram account search
per subcategory and persists the (non-private) results into the profile store.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.services.marketplace_service import MarketplaceService


def build_router(marketplace_service: MarketplaceService, require_feature) -> APIRouter:
    router = APIRouter(prefix="/api/marketplace", tags=["Marketplace"])
    gate = require_feature("marketplace")

    @router.get("/categories")
    def categories(_: dict = Depends(gate)) -> dict:
        return {"categories": marketplace_service.categories()}

    @router.get("/creators")
    def creators(
        category: str = Query(default="generic"),
        limit: int = Query(default=50, ge=1, le=200),
        query: str = Query(default="", max_length=100),
        min_followers: int = Query(default=0, ge=0),
        verified: bool = Query(default=False),
        sort: str = Query(default="followers", pattern="^(followers|media|recent)$"),
        _: dict = Depends(gate),
    ) -> dict:
        return {"creators": marketplace_service.list_creators(
            category, limit, query, min_followers, verified, sort
        )}

    @router.post("/discover")
    def discover(payload: dict, _: dict = Depends(gate)) -> dict:
        key = str(payload.get("category") or "generic").strip()
        limit = int(payload.get("limit") or 20)
        try:
            return marketplace_service.discover(key, limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/save")
    def save(payload: dict, _: dict = Depends(gate)) -> dict:
        username = str(payload.get("username") or "").strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        record = {"username": username, **payload}
        return {"saved": marketplace_service.save(record)}

    @router.post("/favorite")
    def favorite(payload: dict, _: dict = Depends(gate)) -> dict:
        username = str(payload.get("username") or "").strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        try:
            result = marketplace_service.favorite(username)
            return {"saved": result.get("saved", False)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/unfavorite")
    def unfavorite(payload: dict, _: dict = Depends(gate)) -> dict:
        username = str(payload.get("username") or "").strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        try:
            result = marketplace_service.unfavorite(username)
            return {"saved": result.get("saved", False)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.get("/lists")
    def lists(_: dict = Depends(gate)) -> dict:
        return {"lists": marketplace_service.list_lists()}

    @router.post("/lists")
    def create_list(payload: dict, _: dict = Depends(gate)) -> dict:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="list name is required")
        try:
            return marketplace_service.create_list(name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/lists/{list_name}/add")
    def add_to_list(list_name: str, payload: dict, _: dict = Depends(gate)) -> dict:
        username = str(payload.get("username") or "").strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        try:
            return marketplace_service.add_to_list(list_name, username)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/lists/{list_name}/remove")
    def remove_from_list(list_name: str, payload: dict, _: dict = Depends(gate)) -> dict:
        username = str(payload.get("username") or "").strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        try:
            return marketplace_service.remove_from_list(list_name, username)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/lists/{list_name}/members")
    def list_members(list_name: str, _: dict = Depends(gate)) -> dict:
        return {"members": marketplace_service.list_list_members(list_name)}

    return router