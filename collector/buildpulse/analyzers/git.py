"""Commit metadata from the local git repo (or falls back to empty values)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from buildpulse.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult


def _git(repo_root: Path, args: list[str]) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def analyze_git(ctx: AnalyzerContext) -> AnalyzerResult:
    repo = ctx.repo_root
    commit_hash = _git(repo, ["rev-parse", "HEAD"])
    if commit_hash is None:
        ctx.set_tool_version("git", STATUS_SKIPPED)
        return AnalyzerResult("git", STATUS_SKIPPED, {})

    branch = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    message = _git(repo, ["log", "-1", "--pretty=%s"]) or ""
    author = _git(repo, ["log", "-1", "--pretty=%an"]) or ""
    timestamp = _git(repo, ["log", "-1", "--pretty=%cI"]) or ""
    changed_files = _int(_git(repo, ["diff", "--name-only", "HEAD~1", "HEAD"]))
    added = _numstat(repo, "HEAD")

    req = {
        "commit_hash": commit_hash,
        "branch": branch,
        "commit_message": message,
        "commit_author": author,
        "commit_timestamp": timestamp or None,
        "changed_files": changed_files,
        "lines_added": added.get("added"),
        "lines_removed": added.get("removed"),
    }
    ctx.report["build"].update(req)
    ctx.set_tool_version("git", STATUS_OK)
    return AnalyzerResult("git", STATUS_OK, req)


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _numstat(repo_root: Path, base: str) -> dict[str, int | None]:
    out = _git(repo_root, ["diff", "--numstat", f"{base}~1", base])
    added = removed = 0
    if out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                added += int(parts[0])
                removed += int(parts[1])
    return {"added": added, "removed": removed}