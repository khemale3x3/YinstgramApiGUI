from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

JOB_STATUSES = (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    """A unit of background work in CreatorOS.

    Jobs wrap pipeline steps (scrape, analyze, export, ingest, s3 transfers)
    and stream their progress/logs into the job store so the admin UI can
    render live status.
    """

    id: str
    kind: str  # scrape | analyze | export | full | ingest | s3_upload | s3_download
    project: str | None = None
    payload: dict = field(default_factory=dict)
    status: str = STATUS_PENDING
    progress: float = 0.0
    current_step: str = ""
    steps: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    error: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def append_log(self, line: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log.append(f"[{stamp}] {line}")
        if len(self.log) > 2000:
            self.log = self.log[-2000:]
        self.touch()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "project": self.project,
            "payload": dict(self.payload),
            "status": self.status,
            "progress": round(self.progress, 2),
            "current_step": self.current_step,
            "steps": list(self.steps),
            "log": list(self.log),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }