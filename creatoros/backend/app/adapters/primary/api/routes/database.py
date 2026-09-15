from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.services.database_service import DatabaseService


def build_router(database: DatabaseService, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/database", tags=["Database"], dependencies=dependencies)

    @router.get("/status")
    def status(_: dict = Depends(require_admin)):
        return database.status()

    @router.get("/search")
    def search(
        q: str = Query(default="", min_length=1),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        _: dict = Depends(require_admin),
    ):
        offset = (page - 1) * limit
        total = database.search_count(q)
        return {
            "results": database.search(q, limit, offset),
            "total": total,
            "page": page,
            "limit": limit,
        }

    @router.get("/views")
    def views(_: dict = Depends(require_admin)):
        return {"views": database.views(), "status": database.status()}

    @router.get("/tables")
    def tables(_: dict = Depends(require_admin)):
        return {"tables": database.tables(), "status": database.status()}

    @router.get("/profiles/{username}")
    def profile(username: str, _: dict = Depends(require_admin)):
        result = database.get_profile(username)
        if result is None:
            raise HTTPException(status_code=404, detail="profile not found")
        return result

    @router.get("/recent")
    def recent(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        _: dict = Depends(require_admin),
    ):
        return {
            "results": database.recent(limit),
            "total": database.count(),
            "page": page,
            "limit": limit,
        }

    @router.get("/top")
    def top(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=200),
        _: dict = Depends(require_admin),
    ):
        offset = (page - 1) * limit
        return {
            "results": database.top(limit, offset),
            "total": database.count(),
            "page": page,
            "limit": limit,
        }

    return router