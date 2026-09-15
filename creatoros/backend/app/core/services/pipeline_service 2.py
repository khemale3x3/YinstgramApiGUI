from __future__ import annotations
from pathlib import Path
from typing import Callable

from app.core.domain.pipeline import ScraperConfig
from app.core.ports.analyzer import AnalyzerPort
from app.core.ports.database import DatabasePort
from app.core.ports.exporter import ExporterPort
from app.core.ports.scraper import ScraperPort
from app.core.ports.session_source import SessionSourcePort
from app.core.services.project_service import ProjectService
from app.core.config import settings

Emit = Callable[..., None]


class PipelineService:
    """Use case: orchestrate scraper → analyzer → exporter steps as jobs.

    Each `run_*` method is executed inside a JobService worker thread and
    reports through the injected `emit` callback to keep the job's progress,
    steps and logs current in the UI.
    """

    def __init__(
        self,
        scraper: ScraperPort,
        analyzer: AnalyzerPort,
        exporter: ExporterPort,
        sessions: SessionSourcePort,
        projects: ProjectService,
        metadata_db: DatabasePort | None = None,
        ingest_db: DatabasePort | None = None,
        instagram_factory=None,
        instagram_sessions=None,
    ):
        self._scraper = scraper
        self._analyzer = analyzer
        self._exporter = exporter
        self._sessions = sessions
        self._projects = projects
        self._metadata_db = metadata_db
        self._ingest_db = ingest_db
        self._instagram_factory = instagram_factory
        self._instagram_sessions = instagram_sessions

    def run_network_scrape(self, job_id: str, project_name: str, emit: Emit,
                           usernames: list[str], direction: str, amount: int = 100):
        if not self._instagram_factory or not self._instagram_sessions:
            raise ValueError("Instagram account sessions are not configured")
        if self._projects.get_project(project_name) is None:
            raise ValueError(f"project not found: {project_name}")
        session_user = self._instagram_sessions.list_accounts()[0] if self._instagram_sessions.list_accounts() else None
        if not session_user:
            raise ValueError("no Instagram account session available — add one in Accounts")
        client = self._instagram_factory(self._instagram_sessions.load(session_user))
        users = []
        for username in usernames:
            emit(step=f"collecting {direction}", log=f"loading {direction} for @{username}")
            users.extend(client.get_network(username, direction, amount))
        urls = [f"https://www.instagram.com/{user['username']}/" for user in users if user.get("username")]
        added = self._projects.add_urls(project_name, urls)
        emit(progress=100.0, result={"direction": direction, "collected": len(urls), "added": added})
        emit(log=f"{direction} collection complete — {len(urls)} profile URL(s) added to {project_name}")

    # ------------------------------------------------------------------ scrape
    def run_scrape(self, job_id: str, project_name: str, emit: Emit,
                   urls: list[str] | None = None, test_limit: int | None = None):
        project = self._projects.get_project(project_name)
        if project is None:
            raise ValueError(f"project not found: {project_name}")
        if urls is None:
            urls = self._projects.list_urls(project_name)["pending"]
            emit(step="collecting urls", log=f"{len(urls)} pending URL(s)")
        targets = urls
        if test_limit:
            targets = targets[:test_limit]
        if not targets:
            raise ValueError("no pending URLs to scrape")

        self._projects.set_status(project_name, "scraping")
        sessions = self._sessions.all_cookie_sessions()
        if not sessions:
            raise ValueError(
                "no Instagram sessions available — import INSTA_SESSION_* from your .env "
                "in the Sessions admin page"
            )
        config = ScraperConfig(
            max_workers=settings.scraper_max_workers,
            max_posts=settings.scraper_max_posts,
            headless=settings.scraper_headless,
            active_sessions=settings.scraper_active_sessions,
            timeout=settings.scraper_timeout,
            test_mode=settings.scraper_test_mode,
            max_test_profiles=settings.scraper_max_test_profiles,
        )

        output_dir = self._projects.output_dir(project_name)
        emit(step="scraping", log=f"spawning up to {config.max_workers} worker(s)")

        def on_event(event_type: str, message: str = "", **data):
            if event_type == "log":
                emit(log=message)
            elif event_type == "progress":
                emit(progress=data.get("progress", 0.0))
            elif event_type == "profile_saved":
                url = data.get("url", "")
                self._projects.mark_done(project_name, url)
                emit(log=message)
            elif event_type == "profile_failed":
                emit(log=message)
            else:
                emit(log=message or event_type)

        report = self._scraper.scrape(
            urls=targets,
            output_dir=output_dir,
            sessions=sessions,
            config=config,
            on_event=on_event,
            metadata_store=self._metadata_db,
        )

        project = self._projects.get_project(project_name)
        if project is not None:
            project.creators_saved = report.stats.saved
            self._projects.set_status(project_name, "created")

        emit(progress=100.0, result={"stats": report.stats.to_dict()})
        emit(log=f"scrape complete — {report.stats.saved} saved, "
                 f"{report.stats.failed} failed, {len(report.failed_urls)} URL(s) reported")

    # ----------------------------------------------------------------- analyze
    def run_analyze(self, job_id: str, project_name: str, emit: Emit,
                    with_gender: bool = True):
        self._projects.set_status(project_name, "analyzing")
        emit(step="analyzing", log="analyzing scraped creator folders")
        output_dir = self._projects.output_dir(project_name)
        project_root = self._projects.project_root(project_name)

        def on_event(event_type: str, message: str = "", **data):
            if event_type == "log":
                emit(log=message)
            elif event_type == "progress":
                emit(progress=data.get("progress", 0.0))

        report = self._analyzer.analyze(
            output_dir=output_dir,
            project_root=project_root,
            project_name=project_name,
            run_gender=with_gender,
            on_event=on_event,
        )
        project = self._projects.get_project(project_name)
        if project is not None:
            project.outputs = report.outputs
            self._projects.set_status(project_name, "created")

        emit(progress=100.0, result={"analysis": report.__dict__})
        emit(log=f"analysis complete — {report.creators} creators, "
                 f"{report.business} business, {len(report.failed)} failed")

    # ----------------------------------------------------------------- export
    def run_export(self, job_id: str, project_name: str, emit: Emit,
                   with_csv: bool = True, with_jpg: bool = True):
        self._projects.set_status(project_name, "exporting")
        project_root = self._projects.project_root(project_name)
        output_dir = self._projects.output_dir(project_name)
        outputs: list[str] = []

        if with_csv:
            emit(step="csv export", log="writing CSV from analyzed JSON")
            csv_report = self._exporter.export_csv(project_root, project_name)
            emit(log=f"csv export complete — {csv_report.csv_creators} creator rows")
            outputs.extend(csv_report.outputs)

        if with_jpg:
            emit(step="jpg collection", log="collecting profile pictures")
            destination = project_root / "_____all_jpg"
            copied = self._exporter.collect_jpgs(output_dir, destination)
            emit(log=f"jpg collection complete — {copied} file(s) copied")
            if str(destination) not in outputs:
                outputs.append(str(destination))

        project = self._projects.get_project(project_name)
        if project is not None:
            project.outputs = sorted(set([*project.outputs, *outputs]))
            self._projects.set_status(project_name, "done")

        emit(progress=100.0, result={"outputs": outputs})

    # ------------------------------------------------------------------- full
    def run_full(self, job_id: str, project_name: str, emit: Emit,
                 with_gender: bool = True, with_csv: bool = True, with_jpg: bool = True,
                 storage=None, s3_prefix: str | None = None):
        steps = ["scrape", "analyze", "export"]
        emit(steps=steps, step="scrape", log="full pipeline started")
        self.run_scrape(job_id, project_name, emit)
        with_gender_step = "(with gender/logo detection)" if with_gender else "(analysis only)"
        emit(step="analyze", log=f"analyzing {with_gender_step}")
        self.run_analyze(job_id, project_name, emit, with_gender=with_gender)
        emit(step="export", log="exporting CSV and JPGs")
        self.run_export(job_id, project_name, emit, with_csv=with_csv, with_jpg=with_jpg)
        if s3_prefix:
            if storage is None:
                raise ValueError("S3 storage is not configured for this full pipeline job")
            self.upload_project(job_id, project_name, emit, storage, prefix=s3_prefix)
        emit(log="full pipeline finished")

    # -------------------------------------------------------------- database
    def index_profiles(self, emit: Emit) -> dict:
        """Rebuild the local metadata DB from every project's output folders."""
        if self._metadata_db is None:
            raise ValueError("no local metadata database configured")
        before = self._metadata_db.count_profiles()
        indexed = 0
        for project in self._projects.list_projects():
            output_dir = self._projects.output_dir(project.name)
            if not output_dir.exists():
                continue
            for user_dir in sorted(output_dir.iterdir()):
                if not user_dir.is_dir():
                    continue
                user_info_file = user_dir / "userInfo.json"
                post_info_file = user_dir / "postInfo.json"
                if not user_info_file.exists():
                    continue
                import json

                try:
                    with user_info_file.open("r", encoding="utf-8") as fh:
                        profile_info = json.load(fh)
                    post_info = json.loads(post_info_file.read_text("utf-8")) if post_info_file.exists() else {}
                except Exception:
                    continue
                username = user_dir.name
                if self._metadata_db.save_profile(
                    username,
                    f"https://www.instagram.com/{username}/",
                    profile_info,
                    post_info,
                ):
                    indexed += 1
        emit(log=f"indexed {indexed} profile(s) into local metadata store")
        return {"indexed": indexed, "before": before, "after": self._metadata_db.count_profiles()}

    # ------------------------------------------------------------------- s3
    def upload_project(self, job_id: str, project_name: str, emit: Emit,
                       storage, prefix: str = ""):
        root = self._projects.project_root(project_name)
        if not root.exists():
            raise ValueError(f"project folder missing: {root}")
        emit(step="s3 upload", log=f"uploading {root} to s3://{prefix or '<bucket>'}")

        def on_event(event_type: str, message: str = "", **data):
            emit(log=message)

        result = storage.upload_directory(root, prefix=prefix, on_event=on_event)
        emit(progress=100.0, result={"s3_upload": result})
        emit(log=f"uploaded {result.get('files', 0)} file(s)")