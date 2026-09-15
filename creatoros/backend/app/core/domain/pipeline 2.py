from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ScraperConfig:
    """Runtime knobs for the Selenium scraper, all admin-controllable in the UI."""

    max_workers: int = 8
    max_posts: int = 40
    headless: bool = True
    active_sessions: int = 5
    timeout: int = 30
    delay_range: list[float] = field(default_factory=lambda: [2.0, 3.5])
    test_mode: bool = False
    max_test_profiles: int = 5


@dataclass
class ScrapeStats:
    total: int = 0
    saved: int = 0
    failed: int = 0
    posts_saved: int = 0
    locations_found: int = 0
    pictures_downloaded: int = 0
    elapsed_sec: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "saved": self.saved,
            "failed": self.failed,
            "posts_saved": self.posts_saved,
            "locations_found": self.locations_found,
            "pictures_downloaded": self.pictures_downloaded,
            "elapsed_sec": round(self.elapsed_sec, 2),
        }


@dataclass
class ScrapeReport:
    stats: ScrapeStats = field(default_factory=ScrapeStats)
    failed_urls: list[str] = field(default_factory=list)


@dataclass
class AnalyzeReport:
    creators: int = 0
    business: int = 0
    failed: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class ExportReport:
    csv_creators: int = 0
    jpgs_copied: int = 0
    outputs: list[str] = field(default_factory=list)