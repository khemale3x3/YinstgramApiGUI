from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from app.core.services.session_service import SessionService


def build_router(sessions: SessionService, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["Sessions"], dependencies=dependencies)

    @router.get("")
    def list_sessions(_: dict = Depends(require_admin)):
        return {
            "counts": sessions.counts(),
            "sessions": sessions.list(),
        }

    @router.post("/import")
    async def import_env(file: UploadFile, _: dict = Depends(require_admin)):
        content = (await file.read()).decode("utf-8", errors="ignore")
        path = _write_tmp_env(content)
        try:
            imported = sessions.import_from_env(str(path))
        finally:
            path.unlink(missing_ok=True)
        return {"imported": imported}

    @router.get("/instagrapi")
    def list_instagrapi(_: dict = Depends(require_admin)):
        return {"sessions": [s for s in sessions.list() if s.get("kind") == "instagrapi"]}

    return router


def _write_tmp_env(content: str):
    import tempfile
    from pathlib import Path

    path = Path(tempfile.mkdtemp(prefix="creatoros_env_")) / ".env"
    path.write_text(content, "utf-8")
    return path