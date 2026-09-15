from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone

STATUS_CREATED = "created"
STATUS_SCRAPING = "scraping"
STATUS_ANALYZING = "analyzing"
STATUS_EXPORTING = "exporting"
STATUS_DONE = "done"

PROJECT_STATUSES = (
    STATUS_CREATED,
    STATUS_SCRAPING,
    STATUS_ANALYZING,
    STATUS_EXPORTING,
    STATUS_DONE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Project:
    """A named creator-collection run, mirroring the user's Output_<name> layout."""

    name: str
    status: str = STATUS_CREATED
    urls_pending: int = 0
    urls_done: int = 0
    creators_saved: int = 0
    outputs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "urls_pending": self.urls_pending,
            "urls_done": self.urls_done,
            "creators_saved": self.creators_saved,
            "outputs": list(self.outputs),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }