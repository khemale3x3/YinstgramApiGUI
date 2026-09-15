from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.domain.pipeline import ExportReport


class ExporterPort(ABC):
    """Secondary port for CSV export and JPG collection over analyzed output."""

    @abstractmethod
    def export_csv(self, project_root: str | Path, project_name: str) -> ExportReport:
        """Produce <name>.csv from <name>_data.json using the csvmaker logic."""

    @abstractmethod
    def collect_jpgs(self, output_dir: str | Path, destination_dir: str | Path) -> int:
        """Copy every JPG under output_dir into destination (preserving originals)."""