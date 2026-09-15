from __future__ import annotations

import threading
import uuid
from typing import Callable

from app.core.domain.job import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    Job,
)
from app.core.ports.job_store import JobStorePort


class JobService:
    """Use case: manage background jobs and stream their progress.

    `submit` runs a callable in a daemon thread. The callable receives an
    `emit` callback that updates the persisted job atomically, so polling the
    API shows live progress, logs and step state.
    """

    def __init__(self, jobs: JobStorePort):
        self._jobs = jobs
        self._cancel_flags: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, project: str | None = None, steps: list[str] | None = None,
               payload: dict | None = None) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12], kind=kind, project=project,
            steps=list(steps or []), payload=dict(payload or {}),
        )
        return self._jobs.create(job)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> list[Job]:
        return self._jobs.list(limit)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            self._cancel_flags.pop(job_id, None)
        return self._jobs.delete(job_id)

    def emit(self, job_id: str, *, log: str | None = None, progress: float | None = None,
             step: str | None = None, steps: list[str] | None = None,
             result: dict | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if log:
                job.append_log(log)
            if progress is not None:
                job.progress = progress
            if step is not None:
                job.current_step = step
            if steps is not None:
                job.steps = list(steps)
            if result is not None:
                job.result.update(result)
            job.touch()
            self._jobs.update(job)

    def submit(self, job: Job, fn: Callable[[Callable], None]) -> None:
        """Run `fn(emit)` in a background thread, tracking status transitions."""
        cancel = threading.Event()
        with self._lock:
            self._cancel_flags[job.id] = cancel

        def emit(**kwargs):
            if cancel.is_set():
                raise _Cancelled()
            self.emit(job.id, **kwargs)

        def run() -> None:
            try:
                with self._lock:
                    job.status = STATUS_RUNNING
                    self._jobs.update(job)
                self.emit(job.id, log=f"starting job {job.kind}", progress=0.0)
                fn(emit)
                self.emit(job.id, log="job finished", progress=100.0)
                with self._lock:
                    job.status = STATUS_SUCCEEDED
                    job.touch()
                    self._jobs.update(job)
            except _Cancelled:
                with self._lock:
                    job.status = STATUS_CANCELLED
                    job.touch()
                    self._jobs.update(job)
                self.emit(job.id, log="job cancelled")
            except Exception as exc:  # noqa: BLE001 - surface anything to the UI
                with self._lock:
                    job.status = STATUS_FAILED
                    job.error = str(exc)
                    job.touch()
                    self._jobs.update(job)
                try:
                    self.emit(job.id, log=f"job failed: {exc}")
                except Exception:
                    pass
            finally:
                with self._lock:
                    self._cancel_flags.pop(job.id, None)

        thread = threading.Thread(target=run, name=f"job-{job.id}", daemon=True)
        thread.start()

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            cancel = self._cancel_flags.get(job_id)
            job = self._jobs.get(job_id)
            if cancel is None and job is None:
                return False
            if cancel is None and job is not None:
                with self._lock:
                    job.status = STATUS_CANCELLED
                    job.touch()
                    self._jobs.update(job)
                return True
            cancel.set()
            return True


class _Cancelled(Exception):
    """Internal: raised inside a job worker when the job is cancelled."""