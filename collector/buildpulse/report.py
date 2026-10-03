"""Plain-report helpers shared by the collector."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_last_report(repo_root: Path) -> dict[str, Any] | None:
    """Best-effort read of the previous collect run (drives diff-based analyzers)."""
    candidates = [
        repo_root / "build_report.json",
        repo_root / "build" / "build_report.json",
        repo_root / ".codeforge" / "build_report.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    return None


def save_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")