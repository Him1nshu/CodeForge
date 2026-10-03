"""Static analysis wrapper (clang-tidy / cppcheck) with severity mapping."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from codeforge.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult

_LINE_RE = re.compile(
    r"^(?P<file>[^\s]+):(?P<line>\d+)(?::\d+)?:\s+(?P<level>warning|error|note)\s*:\s*(?P<message>.*?)(?:\s*\[(?P<rule>[^\]]+)\])?$"
)


def _severity(level: str) -> str:
    return {"warning": "medium", "error": "high", "note": "low"}.get(level, "low")


def _iter_source_files(repo_root: Path) -> list[Path]:
    suffixes = {".cpp", ".cc", ".cxx", ".c", ".hpp", ".hh", ".h"}
    return sorted(p for p in repo_root.rglob("*") if p.is_file() and p.suffix in suffixes and "build" not in p.parts)


def analyze_static_analysis(ctx: AnalyzerContext) -> AnalyzerResult:
    tool = shutil.which("clang-tidy") or shutil.which("cppcheck")
    if tool is None:
        ctx.report["static_analysis"] = []
        ctx.set_tool_version("static-analysis", STATUS_SKIPPED)
        return AnalyzerResult("static_analysis", STATUS_SKIPPED, {"static_analysis": []})

    files = _iter_source_files(ctx.repo_root)
    if not files:
        ctx.report["static_analysis"] = []
        return AnalyzerResult("static_analysis", STATUS_OK, {"static_analysis": [], "note": "no source files"})

    cmd = [tool, "--enable=all", "--quiet"]
    if "cppcheck" in tool:
        cmd.append("--language=c++")
    cmd += [str(f) for f in files]
    result = subprocess.run(cmd, cwd=ctx.repo_root, capture_output=True, text=True, timeout=1800, check=False)
    output = result.stdout + result.stderr

    issues: list[dict] = []
    for match in _LINE_RE.finditer(output):
        issues.append(
            {
                "tool": "cppcheck" if "cppcheck" in tool else "clang-tidy",
                "file": match.group("file"),
                "line": int(match.group("line")),
                "severity": _severity(match.group("level")),
                "rule": match.group("rule"),
                "message": match.group("message").strip(),
                "category": "code-smell",
            }
        )
    ctx.report["static_analysis"] = issues
    ctx.set_tool_version("static-analysis", STATUS_OK)
    return AnalyzerResult("static_analysis", STATUS_OK, {"static_analysis": issues})