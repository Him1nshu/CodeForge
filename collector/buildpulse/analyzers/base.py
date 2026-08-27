"""Analyzer plugin context, protocol, and result types.

Each analyzer is a small pure-ish function of the workspace + config that feeds
one or more sections of build_report.json. Analyzers never fail the collect
run: a missing tool produces an empty/lazy section plus a note in
`build.environment.tool_versions` (status UNSUPPORTED/SKIPPED).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STATUS_OK = "ok"
STATUS_SKIPPED = "skipped"
STATUS_UNSUPPORTED = "unsupported"


@dataclass
class AnalyzerContext:
    """Everything an analyzer may need, without touching the network."""

    repo_root: Path
    config: dict[str, Any]
    report: dict[str, Any] = field(default_factory=dict)
    created: dict[str, Any] = field(default_factory=dict)

    def set_tool_version(self, tool: str, state: str) -> None:
        env = self.report["build"]["environment"]
        versions = env.get("tool_versions", {})
        versions[tool] = state
        env["tool_versions"] = versions


@dataclass
class AnalyzerResult:
    """What one analyzer produced."""

    name: str
    status: str
    request: dict[str, Any]
    note: str = ""


Analyzer = Callable[[AnalyzerContext], AnalyzerResult]


def run_command(command: str, cwd: Path, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Execute an arbitrary shell command line (honors `&&`, redirects, quotes)."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 1800)
    if sys.platform == "win32":
        return subprocess.run(["cmd", "/c", command], cwd=cwd, check=False, **kwargs)
    return subprocess.run(["sh", "-c", command], cwd=cwd, check=False, **kwargs)


def resolve_command(command: str | None, repo_root: Path) -> str | None:
    """Resolve the first token of a shell command via PATH or the repo root."""
    if not command:
        return None
    tool = command.split()[0]
    return shutil.which(tool) or (str((repo_root / tool).resolve()) if (repo_root / tool).is_file() else None)