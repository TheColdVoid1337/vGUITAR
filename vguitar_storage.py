"""Local-only preference and quiz-history persistence for vGUITAR.

No network or third-party dependencies. All user data stays next to the app.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 1


def app_home() -> Path:
    """Distribution-relative paths; env override allows isolated tests."""
    return Path(os.environ.get("VGUITAR_DATA_DIR", Path(__file__).resolve().parent)).resolve()


def settings_dir() -> Path:
    return app_home() / "settings"


def results_dir() -> Path:
    return app_home() / "results"


def preferences_path() -> Path:
    return settings_dir() / "note_trainer.json"


def ensure_dirs() -> None:
    settings_dir().mkdir(parents=True, exist_ok=True)
    results_dir().mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def read_preferences() -> dict[str, Any]:
    try:
        data = json.loads(preferences_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_preferences(data: dict[str, Any]) -> None:
    atomic_write_json(preferences_path(), data)


def save_run(run: dict[str, Any]) -> Path:
    """Create an immutable result record with a collision-resistant basename."""
    ensure_dirs()
    if not run.get("run_id") or not run.get("finished_at"):
        raise ValueError("Missing run metadata")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = results_dir() / f"{stamp}_{run['run_id']}.json"
    if path.exists():
        raise FileExistsError(path)
    atomic_write_json(path, run)
    return path


def list_runs() -> tuple[list[dict[str, Any]], int]:
    """Newest first; ignore corrupt/unrecognized files, count skipped."""
    if not results_dir().exists():
        return [], 0
    runs: list[dict[str, Any]] = []
    invalid = 0
    for path in results_dir().glob("*.json"):
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(content, dict) or not isinstance(content.get("questions"), list) or not content.get("run_id"):
                raise ValueError("Not a vGUITAR run")
            content["_filename"] = path.name
            runs.append(content)
        except (OSError, ValueError, TypeError):
            invalid += 1
    runs.sort(key=lambda x: (x.get("finished_at", ""), x.get("run_id", "")), reverse=True)
    return runs, invalid


def run_statistics(run: dict[str, Any]) -> dict[str, Any]:
    items = run.get("questions", [])
    count = len(items)
    correct = sum(bool(x.get("correct")) for x in items)
    elapsed = [float(x["response_seconds"]) for x in items if isinstance(x.get("response_seconds"), (int, float))]
    # Aggregates and per-string timings provide learning signals even when accuracy ties.
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get("string_number", "?"))
        groups.setdefault(key, []).append(item)
    by_string = {}
    for key, records in sorted(groups.items()):
        times = [float(x["response_seconds"]) for x in records if isinstance(x.get("response_seconds"), (int, float))]
        by_string[key] = {
            "questions": len(records),
            "correct": sum(bool(x.get("correct")) for x in records),
            "average_seconds": round(statistics.mean(times), 3) if times else None,
        }
    return {
        "total": count,
        "correct": correct,
        "accuracy_percent": round(100 * correct / count, 1) if count else 0.0,
        "mean_seconds": round(statistics.mean(elapsed), 3) if elapsed else None,
        "median_seconds": round(statistics.median(elapsed), 3) if elapsed else None,
        "fastest_seconds": round(min(elapsed), 3) if elapsed else None,
        "slowest_seconds": round(max(elapsed), 3) if elapsed else None,
        "by_string": by_string,
        "wrong_notes": dict(Counter(str(x.get("expected_note", "?")) for x in items if not x.get("correct"))),
    }


def export_runs_for_llm(runs: list[dict[str, Any]]) -> str:
    """Clipboard-friendly structured text, detailed enough to diagnose slow notes."""
    if not runs:
        raise ValueError("No selected runs")
    payload = {
        "format": "vGUITAR_NOTE_TRAINER_REPORT",
        "schema_version": SCHEMA_VERSION,
        "run_count": len(runs),
        "runs": [],
    }
    for run in runs:
        payload["runs"].append({
            "run_id": run.get("run_id"),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "configuration": run.get("configuration", {}),
            "statistics": run_statistics(run),
            "questions": run.get("questions", []),
        })
    return json.dumps(payload, ensure_ascii=False, indent=2)
