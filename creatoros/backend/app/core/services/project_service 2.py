from __future__ import annotations
import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.domain.project import PROJECT_STATUSES, Project
from app.core.ports.project_store import ProjectStorePort

_USERNAME_RE = re.compile(r"[A-Za-z0-9_.]{1,30}")


def resolve_username(url_or_username: str) -> str:
    """Accept a full Instagram URL or a bare username; return the username."""
    text = (url_or_username or "").strip().rstrip("/").lstrip("@")
    if not text:
        raise ValueError("empty username")
    if "instagram.com" in text:
        parsed = urlparse(text if "://" in text else f"https://{text}")
        segment = (parsed.path or "").strip("/").split("/")[0]
        if segment:
            return segment.split("?")[0]
    return text.split("?")[0]


def resolve_profile_url(username: str) -> str:
    return f"https://www.instagram.com/{username}/"


class ProjectService:
    """Use case: projects + their URL lists (the input.csv ↔ inputdone.csv flow)."""

    def __init__(self, projects: ProjectStorePort, data_dir: str | Path):
        self._projects = projects
        self._data_dir = Path(data_dir)

    # ------------------------------------------------------------------ paths
    def project_root(self, name: str) -> Path:
        return self._data_dir / f"Output_{name}"

    def output_dir(self, name: str) -> Path:
        return self.project_root(name) / "output"

    # -------------------------------------------------------------- lifecycle
    def list_projects(self) -> list[Project]:
        return self._projects.list()

    def get_project(self, name: str) -> Project | None:
        return self._projects.get(name)

    def create_project(self, name: str) -> Project:
        clean = name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
        if not clean:
            raise ValueError("project name cannot be empty")
        existing = self._projects.get(clean)
        if existing:
            return existing
        root = self.project_root(clean)
        root.mkdir(parents=True, exist_ok=True)
        (root / "output").mkdir(exist_ok=True)
        self._ensure_url_files(clean)
        project = Project(name=clean)
        return self._projects.create(project)

    def delete_project(self, name: str) -> bool:
        return self._projects.delete(name)

    def set_status(self, name: str, status: str) -> Project | None:
        if status not in PROJECT_STATUSES:
            raise ValueError(f"invalid status: {status}")
        project = self._projects.get(name)
        if project is None:
            return None
        project.status = status
        project.touch()
        return self._projects.update(project)

    # ------------------------------------------------------------------- urls
    def _ensure_url_files(self, name: str) -> None:
        root = self.project_root(name)
        for fname in ("input.csv", "inputdone.csv"):
            path = root / fname
            if not path.exists():
                with path.open("w", newline="", encoding="utf-8") as fh:
                    if fname == "input.csv":
                        csv.writer(fh).writerow(["url"])
                    else:
                        csv.writer(fh).writerow(["url", "processed_at"])

    def add_urls(self, name: str, entries: list[str]) -> int:
        urls = []
        for entry in entries:
            username = resolve_username(entry)
            urls.append(resolve_profile_url(username))
        added = self._projects.add_urls(name, urls, done=False)
        if added:
            self._sync_url_files(name)
            self._refresh_counts(name)
        return added

    def remove_urls(self, name: str, entries: list[str]) -> int:
        usernames = [resolve_username(entry) for entry in entries]
        urls = [resolve_profile_url(u) for u in usernames]
        removed = self._projects.remove_pending(name, urls)
        if removed:
            self._sync_url_files(name)
            self._refresh_counts(name)
        return removed

    def import_csv(self, name: str, csv_text: str) -> int:
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise ValueError("CSV must include a header row")
        column = "url" if "url" in reader.fieldnames else reader.fieldnames[0]
        entries = [row[column] for row in reader if row.get(column, "").strip()]
        if not entries:
            raise ValueError("no URLs found in CSV")
        return self.add_urls(name, entries)

    def list_urls(self, name: str) -> dict:
        pending = self._projects.pending_urls(name)
        done = self._projects.done_urls(name)
        return {
            "pending": pending,
            "done": done,
            "pending_count": len(pending),
            "done_count": len(done),
        }

    def mark_done(self, name: str, url: str) -> bool:
        moved = self._projects.mark_done(name, url)
        if moved:
            self._sync_url_files(name)
            self._refresh_counts(name)
        return moved

    def failed_urls(self, name: str, entries: list[str]) -> int:
        """Move failed URLs back to pending so they re-run on the next scrape."""
        usernames = [resolve_username(entry) for entry in entries]
        urls = [resolve_profile_url(u) for u in usernames]
        moved = 0
        for url in urls:
            if self._projects.remove_pending(name, [url]) and True:
                # remove_pending already removed; re-add below atomically
                pass
            moved += self._projects.add_urls(name, [url], done=False)
        if moved:
            self._sync_url_files(name)
            self._refresh_counts(name)
        return moved

    # --------------------------------------------------------------- internal
    def _sync_url_files(self, name: str) -> None:
        root = self.project_root(name)
        root.mkdir(parents=True, exist_ok=True)
        pending = self._projects.pending_urls(name)
        done = self._projects.done_urls(name)
        with (root / "input.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url"])
            writer.writerows([[u] for u in pending])
        with (root / "inputdone.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url", "processed_at"])
            writer.writerows(
                [[u, datetime.now(timezone.utc).isoformat()] for u in done]
            )

    def _refresh_counts(self, name: str) -> None:
        project = self._projects.get(name)
        if project is None:
            return
        project.urls_pending = len(self._projects.pending_urls(name))
        project.urls_done = len(self._projects.done_urls(name))
        project.touch()
        self._projects.update(project)