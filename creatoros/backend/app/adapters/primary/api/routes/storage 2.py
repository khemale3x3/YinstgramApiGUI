from __future__ import annotations
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.services.storage_service import StorageService


def build_router(storage: StorageService, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/storage", tags=["Storage"], dependencies=dependencies)

    @router.get("/status")
    def status(_: dict = Depends(require_admin)):
        return storage.status()

    @router.get("/list")
    def list_keys(prefix: str = Query(default=""), _: dict = Depends(require_admin)):
        try:
            return {"keys": storage.list_keys(prefix)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/download")
    def download(
        key: str = Query(min_length=1), destination: str | None = None,
        _: dict = Depends(require_admin),
    ):
        if not destination:
            import tempfile
            from pathlib import Path

            tmp = Path(tempfile.mkdtemp(prefix="creatoros_download_")) / (key.split("/")[-1] or "file")
            try:
                storage.download_file(key, tmp)
                with open(tmp, "rb") as fh:
                    data = fh.read()
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            finally:
                tmp.unlink(missing_ok=True)
            return StreamingResponse(
                io.BytesIO(data),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{key.split("/")[-1]}"'},
            )
        try:
            local = storage.download_file(key, destination)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"downloaded_to": local}

    @router.post("/upload", status_code=201)
    async def upload_file(
        key: str = Query(min_length=1), file: UploadFile = None,
        _: dict = Depends(require_admin),
    ):
        if file is None:
            raise HTTPException(status_code=400, detail="file body required for in-memory upload")
        content = await file.read()
        local = _write_tmp(content, file.filename or key.split("/")[-1])
        try:
            try:
                stored_key = storage.upload_file(local, key)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            local.unlink(missing_ok=True)
        return {"key": stored_key}

    return router


def _write_tmp(content: bytes, name: str):
    import tempfile
    from pathlib import Path

    path = Path(tempfile.mkdtemp(prefix="creatoros_upload_")) / name
    path.write_bytes(content)
    return path