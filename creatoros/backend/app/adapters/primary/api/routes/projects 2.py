from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.adapters.primary.api.schemas import ProjectCreateRequest, UrlListRequest, UrlRemoveRequest
from app.core.services.project_service import ProjectService


def build_router(projects: ProjectService, require_admin, dependencies=None) -> APIRouter:
    router = APIRouter(prefix="/api/projects", tags=["Projects"], dependencies=dependencies)

    @router.get("")
    def list_projects(_: dict = Depends(require_admin)):
        return {"projects": [p.to_dict() for p in projects.list_projects()]}

    @router.get("/{name}")
    def get_project(name: str, _: dict = Depends(require_admin)):
        project = projects.get_project(name)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return project.to_dict()

    @router.post("", status_code=201)
    def create_project(payload: ProjectCreateRequest, _: dict = Depends(require_admin)):
        try:
            project = projects.create_project(payload.name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return project.to_dict()

    @router.delete("/{name}")
    def delete_project(name: str, _: dict = Depends(require_admin)):
        if not projects.delete_project(name):
            raise HTTPException(status_code=404, detail="project not found")
        return {"deleted": True}

    @router.get("/{name}/urls")
    def list_urls(name: str, _: dict = Depends(require_admin)):
        if projects.get_project(name) is None:
            raise HTTPException(status_code=404, detail="project not found")
        return projects.list_urls(name)

    @router.post("/{name}/urls", status_code=201)
    def add_urls(name: str, payload: UrlListRequest, _: dict = Depends(require_admin)):
        if projects.get_project(name) is None:
            raise HTTPException(status_code=404, detail="project not found")
        try:
            added = projects.add_urls(name, payload.urls)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"added": added, **projects.list_urls(name)}

    @router.post("/{name}/urls/upload", status_code=201)
    async def upload_urls(name: str, file: UploadFile, _: dict = Depends(require_admin)):
        if projects.get_project(name) is None:
            raise HTTPException(status_code=404, detail="project not found")
        content = (await file.read()).decode("utf-8", errors="ignore")
        try:
            added = projects.import_csv(name, content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"added": added, "filename": file.filename, **projects.list_urls(name)}

    @router.post("/{name}/urls/remove")
    def remove_urls(name: str, payload: UrlRemoveRequest, _: dict = Depends(require_admin)):
        try:
            removed = projects.remove_urls(name, payload.urls)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"removed": removed, **projects.list_urls(name)}

    @router.post("/{name}/urls/failed")
    def requeue_failed(name: str, payload: UrlRemoveRequest, _: dict = Depends(require_admin)):
        """Move failed URLs back to the pending list for the next run."""
        moved = projects.failed_urls(name, payload.urls)
        return {"requeued": moved, **projects.list_urls(name)}

    return router