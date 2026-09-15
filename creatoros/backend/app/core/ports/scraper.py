from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.domain.pipeline import ScrapeReport


class ScraperPort(ABC):
    """Secondary port for the Selenium web scraper.

    The implementation is a clean port of the user's iteration01scraper.py —
    multi-session headless Chrome, GraphQL network capture, per-username JSON
    output and optional metadata persistence.
    """

    @abstractmethod
    def scrape(
        self,
        urls: list[str],
        output_dir: str | Path,
        sessions: list[str],
        config,
        on_event=None,
        metadata_store=None,
    ) -> ScrapeReport:
        """Scrape a list of profile URLs into output_dir.

        `on_event(event_type, message, **data)` is invoked for progress/log
        updates. `metadata_store`, when given, receives each saved profile via
        its `save_profile` method.
        """