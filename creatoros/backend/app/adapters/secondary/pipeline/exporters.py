"""Exporter adapter — CSV export (csvmaker logic) and JPG collection."""
from __future__ import annotations

import importlib
import shutil
from pathlib import Path

from app.core.domain.pipeline import ExportReport
from app.core.ports.exporter import ExporterPort

CSV_MODULE = "csvmaker"
JPG_MODULE = "jpg_collector"


def _load(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{name} unavailable: {exc}") from exc


class PipelineExporterAdapter(ExporterPort):
    """Driven adapter implementing ExporterPort over the copied exporter scripts."""

    def export_csv(self, project_root, project_name):
        project_root = Path(project_root)
        data_json = project_root / f"{project_name}_data.json"
        output_csv = project_root / f"{project_name}.csv"
        report = ExportReport()

        if not data_json.exists():
            raise FileNotFoundError(f"{data_json} not found — run the analyzer step first")

        try:
            mod = _load(CSV_MODULE)
            success, total = mod.create_csv_from_analyzed_json_efficiently(
                str(data_json), str(output_csv)
            )
            if success:
                report.csv_creators = int(total or 0)
                report.outputs.append(str(output_csv))
        except Exception as exc:
            raise RuntimeError(f"csv export failed: {exc}") from exc
        return report

    def collect_jpgs(self, output_dir, destination_dir):
        output_dir = Path(output_dir)
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for jpg_file in sorted(output_dir.rglob("*.jpg")):
            target = destination_dir / jpg_file.name
            if target.exists():
                stem, suffix = jpg_file.stem, jpg_file.suffix
                counter = 1
                while target.exists():
                    target = destination_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            shutil.copy2(str(jpg_file), str(target))
            copied += 1
        return copied