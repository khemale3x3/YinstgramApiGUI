from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.primary.api.schemas import JobCreateRequest
from app.core.domain.job import STATUS_CANCELLED, STATUS_FAILED
from app.core.services.database_service import DatabaseService
from app.core.services.job_service import JobService
from app.core.services.pipeline_service import PipelineService
from app.core.services.project_service import ProjectService
from app.core.services.storage_service import StorageService


def build_router(
    jobs: JobService,
    pipeline: PipelineService,
    database: DatabaseService,
    storage: StorageService,
    projects: ProjectService,
    require_admin,
    dependencies=None,
) -> APIRouter:
    router = APIRouter(prefix="/api/jobs", tags=["Jobs"], dependencies=dependencies)

    @router.get("")
    def list_jobs(limit: int = Query(default=50, ge=1, le=200), _: dict = Depends(require_admin)):
        return {"jobs": [j.to_dict() for j in jobs.list(limit)]}

    @router.get("/{job_id}")
    def get_job(job_id: str, _: dict = Depends(require_admin)):
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job.to_dict()

    @router.post("", status_code=201)
    def create_job(payload: JobCreateRequest, _: dict = Depends(require_admin)):
        """Submit a pipeline/database/storage job for background execution."""
        if payload.kind in ("scrape", "network_scrape", "analyze", "export", "full") and not payload.project:
            raise HTTPException(status_code=400, detail="project is required for this job kind")

        job = jobs.create(payload.kind, payload.project, payload=payload.model_dump(exclude_none=True))

        try:
            dispatch(jobs, pipeline, database, storage, projects, job, payload)
        except HTTPException:
            jobs.delete(job.id)
            raise

        return job.to_dict()

    @router.post("/{job_id}/retry")
    def retry_job(job_id: str, _: dict = Depends(require_admin)):
        """Re-run a failed/cancelled job using its stored creation payload."""
        prev = jobs.get(job_id)
        if prev is None:
            raise HTTPException(status_code=404, detail="job not found")
        if prev.status not in (STATUS_FAILED, STATUS_CANCELLED):
            raise HTTPException(status_code=400, detail="only failed or cancelled jobs can be retried")
        try:
            payload = JobCreateRequest(**dict(prev.payload or {}))
        except Exception as exc:  # noqa: BLE001 - invalid stored payload
            raise HTTPException(status_code=422, detail=f"stored job payload is not retryable: {exc}")
        job = jobs.create(payload.kind, payload.project, payload=payload.model_dump(exclude_none=True))
        dispatch(jobs, pipeline, database, storage, projects, job, payload)
        return job.to_dict()

    @router.post("/{job_id}/cancel")
    def cancel_job(job_id: str, _: dict = Depends(require_admin)):
        return {"cancelled": jobs.cancel(job_id)}

    @router.delete("/{job_id}")
    def delete_job(job_id: str, _: dict = Depends(require_admin)):
        return {"deleted": jobs.delete(job_id)}

    return router


def dispatch(jobs, pipeline, database, storage, projects, job, payload) -> None:
    """Route a JobCreateRequest payload onto the right background worker."""
    if payload.kind == "scrape":
        jobs.submit(
            job,
            lambda e: pipeline.run_scrape(
                job.id, payload.project, e,
                urls=payload.urls, test_limit=payload.test_limit,
            ),
        )
    elif payload.kind == "network_scrape":
        usernames = payload.usernames or ([payload.username] if payload.username else [])
        if not usernames or not payload.direction:
            raise HTTPException(status_code=400, detail="username(s) and direction are required")
        jobs.submit(
            job,
            lambda e: pipeline.run_network_scrape(
                job.id, payload.project, e, usernames, payload.direction, payload.test_limit or 100
            ),
        )
    elif payload.kind == "analyze":
        jobs.submit(
            job,
            lambda e: pipeline.run_analyze(
                job.id, payload.project, e, with_gender=payload.with_gender
            ),
        )
    elif payload.kind == "export":
        jobs.submit(
            job,
            lambda e: pipeline.run_export(
                job.id, payload.project, e,
                with_csv=payload.with_csv, with_jpg=payload.with_jpg,
            ),
        )
    elif payload.kind == "full":
        jobs.submit(
            job,
            lambda e: pipeline.run_full(
                job.id, payload.project, e,
                with_gender=payload.with_gender,
                with_csv=payload.with_csv,
                with_jpg=payload.with_jpg,
                storage=storage if payload.s3_prefix else None,
                s3_prefix=payload.s3_prefix,
            ),
        )
    elif payload.kind == "index":
        jobs.submit(job, lambda e: pipeline.index_profiles(e))
    elif payload.kind == "ingest":
        if not payload.source:
            raise HTTPException(status_code=400, detail="source (keylist path) required for ingest")
        jobs.submit(
            job,
            lambda e: _run_ingest(database, payload, e),
        )
    elif payload.kind == "s3_upload":
        source = payload.source or (
            projects.project_root(payload.project).as_posix() if payload.project else None
        )
        if not source:
            raise HTTPException(status_code=400, detail="source (local path or project) required for s3_upload")
        jobs.submit(
            job,
            lambda e: _run_upload(storage, source, payload.s3_prefix or "", e),
        )
    else:
        raise HTTPException(status_code=400, detail=f"unsupported job kind: {payload.kind}")


def _run_ingest(database: DatabaseService, payload: JobCreateRequest, emit):
    return database.ingest(payload.source, on_event=emit, table=payload.table)


def _run_upload(storage: StorageService, source: str, prefix: str, emit):
    result = storage.upload_directory(source, prefix=prefix, on_event=emit)
    emit(progress=100.0, result={"s3_upload": result})
    emit(log=f"uploaded {result.get('files', 0)} file(s)")