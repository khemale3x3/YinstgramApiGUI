from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.domain.creator import Creator
from app.core.domain.post import CreatorPost
from app.core.services.instagram_service import InstagramService


def build_router(creators: InstagramService, require_admin=None, dependencies=None) -> APIRouter:
    """Build the creators router with its dependency injected."""
    router = APIRouter(prefix="/api/creators", tags=["Creators"])
    default_deps = ([Depends(require_admin)] if require_admin else []) + list(dependencies or [])

    @router.get("/{username}", response_model=Creator, dependencies=default_deps)
    def get_creator(username: str) -> Creator:
        try:
            return creators.get_creator(username)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/{username}/posts", response_model=list[CreatorPost], dependencies=default_deps)
    def get_creator_posts(
        username: str,
        amount: int = Query(default=10, ge=1, le=100),
    ) -> list[CreatorPost]:
        try:
            return creators.get_creator_posts(username, amount)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router