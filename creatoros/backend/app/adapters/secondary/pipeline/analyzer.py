"""Analyzer adapter — wraps the copied analyze_insta_except.py pipeline.

The heavy ML stack (ultralytics/transformers) is only required when `run_gender`
is enabled, so this adapter imports the module lazily and degrades to a
text-only analysis when the model dependencies are unavailable on the host.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from app.core.domain.pipeline import AnalyzeReport
from app.core.ports.analyzer import AnalyzerPort

MODULE_NAME = "analyze_insta_except"


class AnalyzerUnavailableError(RuntimeError):
    pass


def _module():
    import importlib

    try:
        return importlib.import_module(MODULE_NAME)
    except Exception as exc:  # noqa: BLE001
        raise AnalyzerUnavailableError(
            f"analyzer module unavailable: {exc}. "
            "Ensure pipeline scripts are present and their dependencies (e.g. "
            "colorama, tqdm, pillow) are installed."
        ) from exc


class PipelineAnalyzerAdapter(AnalyzerPort):
    """Driven adapter implementing AnalyzerPort over the user's analyzer scripts."""

    def analyze(self, output_dir, project_root, project_name, run_gender=True, on_event=None):
        output_dir = Path(output_dir)
        project_root = Path(project_root)
        project_root.mkdir(parents=True, exist_ok=True)

        def emit(event_type, message="", **data):
            if on_event:
                try:
                    on_event(event_type, message, **data)
                except Exception:
                    pass

        mod = _module()
        creators_to_analyze = [
            d for d in sorted(os.listdir(output_dir))
            if (output_dir / d).is_dir()
        ]
        if not creators_to_analyze:
            emit("log", "no creator folders found under output/")
            return AnalyzeReport()

        # ------------------------------------------------------- gender phase
        gender_lookup: dict = {}
        logo_folders: set = set()
        if run_gender:
            emit("log", "gender/age detection requested — checking model availability")
            try:
                detector = mod.Detector()
                for idx, folder in enumerate(creators_to_analyze):
                    username = folder
                    user_info_path = output_dir / folder / "userInfo.json"
                    if user_info_path.exists():
                        try:
                            ui = mod.load_json_file(str(user_info_path))
                            username = ui.get("data", {}).get("user", {}).get("username", folder) or folder
                        except Exception:
                            pass
                    try:
                        result = detector.detect(username, local_dir=str(output_dir))
                    except Exception as exc:
                        emit("log", f"gender detection failed for @{username}: {exc}")
                        result = {
                            "gender": "Unknown", "age_group": "Unknown",
                            "detection_status": f"Error: {exc}",
                        }
                    if result.get("gender") == "Unknown":
                        try:
                            is_logo, conf, label = detector.check_logo(username, local_dir=str(output_dir))
                            result["is_logo"], result["logo_confidence"], result["logo_label"] = (
                                is_logo, conf, label,
                            )
                            if is_logo:
                                logo_folders.add(folder)
                        except Exception:
                            pass
                    gender_lookup[username] = result
                    emit(
                        "log",
                        f"gender [{idx + 1}/{len(creators_to_analyze)}] @{username}: "
                        f"{result.get('gender') or 'Unknown'} / {result.get('age_group') or 'Unknown'}",
                    )
                emit("log", f"gender detection complete ({len(logo_folders)} logo account(s) excluded)")
            except AnalyzerUnavailableError:
                emit("log", "gender detection unavailable (ML deps missing) — skipping")
            except Exception as exc:
                emit("log", f"gender detection skipped: {exc}")
        else:
            emit("log", "gender/age detection disabled by request")

        creators_to_analyze = [c for c in creators_to_analyze if c not in logo_folders]

        # ------------------------------------------------------- analysis phase
        analyzed_results: list[dict] = []
        ai_results: list[dict] = []
        biz_analyzed: list[dict] = []
        biz_ai: list[dict] = []
        failed: list[str] = []

        total = len(creators_to_analyze)
        for idx, folder in enumerate(creators_to_analyze, start=1):
            try:
                result = mod.analyze_creator_data(str(output_dir / folder), gender_lookup)
                if not result:
                    failed.append(folder)
                    emit("log", f"[{idx}/{total}] skipped @{folder}: no data")
                    continue
                acct_type = result.get("account_type", 1)
                if acct_type == 2:
                    biz_analyzed.append(result["analyzed"])
                    biz_ai.append(result["ai_analyzed"])
                else:
                    analyzed_results.append(result["analyzed"])
                    ai_results.append(result["ai_analyzed"])
                emit("log", f"[{idx}/{total}] analyzed @{folder}")
            except Exception as exc:
                failed.append(folder)
                emit("log", f"[{idx}/{total}] error @{folder}: {exc}")
            if on_event:
                try:
                    on_event("progress", "", progress=(idx / total) * 100)
                except Exception:
                    pass

        # ------------------------------------------------------------ outputs
        today = datetime.datetime.now().strftime("%Y%m%d")
        outputs: list[str] = []
        low_bad_lines: list[str] = []
        sanitize_stats = {}

        def save_json_and_jsonl(analyzed_list, ai_list, json_name, jsonl_name, label):
            if not analyzed_list and not ai_list:
                emit("log", f"no {label} results to save")
                return
            json_path = project_root / json_name
            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "total_creators_analyzed": len(analyzed_list),
                        "creators": analyzed_list,
                    },
                    fh,
                    indent=2,
                    ensure_ascii=False,
                )
            outputs.append(str(json_path))
            if ai_list:
                good_lines, stats = mod.sanitize_ai_records(ai_list, label, low_bad_lines)
                sanitize_stats[label] = stats
                jsonl_path = project_root / jsonl_name
                with jsonl_path.open("w", encoding="utf-8") as fh:
                    for line in good_lines:
                        fh.write(line + "\n")
                outputs.append(str(jsonl_path))
                emit(
                    "log",
                    f"[{label}] {len(good_lines)} clean of {len(ai_list)} "
                    f"(low-post {stats.get('low_post', 0)}, bad {stats.get('bad', 0)}, "
                    f"auto-fixed {stats.get('auto_fixed', 0)})",
                )

        save_json_and_jsonl(
            analyzed_results, ai_results, f"{project_name}_data.json", f"{project_name}.jsonl",
            "creator (type 1&3)",
        )
        save_json_and_jsonl(
            biz_analyzed, biz_ai, f"{project_name}_business_data.json", f"{project_name}_business.jsonl",
            "business (type 2)",
        )

        if low_bad_lines:
            reject_path = project_root / f"{project_name}_low_bad.jsonl"
            with reject_path.open("w", encoding="utf-8") as fh:
                for line in low_bad_lines:
                    fh.write(line + "\n")
            outputs.append(str(reject_path))

        if analyzed_results:
            csv_path = project_root / f"output{today}.csv"
            try:
                ok, rows = mod.write_analyzed_csv(analyzed_results, str(csv_path), is_business=False)
                if ok:
                    outputs.append(str(csv_path))
                    emit("log", f"creator CSV written ({rows} rows)")
            except Exception as exc:
                emit("log", f"creator CSV failed: {exc}")
        if biz_analyzed:
            csv_path = project_root / f"output{today}_business.csv"
            try:
                ok, rows = mod.write_analyzed_csv(biz_analyzed, str(csv_path), is_business=True)
                if ok:
                    outputs.append(str(csv_path))
                    emit("log", f"business CSV written ({rows} rows)")
            except Exception as exc:
                emit("log", f"business CSV failed: {exc}")

        emit("log", f"analysis finished — {len(analyzed_results)} creator(s), "
                    f"{len(biz_analyzed)} business, {len(failed)} failed")
        return AnalyzeReport(
            creators=len(analyzed_results),
            business=len(biz_analyzed),
            failed=failed,
            outputs=outputs,
        )