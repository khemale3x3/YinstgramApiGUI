from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.domain.pipeline import AnalyzeReport


class AnalyzerPort(ABC):
    """Secondary port for creator analysis (gender/age/logo, bio location,
    niche, pricing, collaborations, email/phone extraction)."""

    @abstractmethod
    def analyze(
        self,
        output_dir: str | Path,
        project_root: str | Path,
        project_name: str,
        run_gender: bool = True,
        on_event=None,
    ) -> AnalyzeReport:
        """Analyze every output/<username>/ folder and write:

        - <name>_data.json        (wide dump)
        - <name>.jsonl            (AI-facing records)
        - <name>_csv rows / output<date>.csv
        """