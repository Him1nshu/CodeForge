"""Build runner + warnings/errors + artifact metrics.

Executes the configured configure/build commands, times the build, and
sweeps the captured output for compiler warning/error counts. Supports the
CLI-relevant formats: GCC/Clang/javac `warning:`/`error:` lines, Maven
`[WARNING]`/`[ERROR]` lines, and Gradle `warning:`/`error:` output. Missing
build tooling yields a skipped section rather than a crashed run.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from buildpulse.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult, resolve_command, run_command
from buildpulse.report import utcnow_iso

_JAVAC_WARNING_RE = re.compile(r"\b(?:warning|warn):\s", re.IGNORECASE)
_JAVAC_ERROR_RE = re.compile(r"\b(?:error|fatal error):\s", re.IGNORECASE)
_BRACKET_WARNING_RE = re.compile(r"\[WARNING\]", re.IGNORECASE)
_BRACKET_ERROR_RE = re.compile(r"\[ERROR\]", re.IGNORECASE)
_FAILURE_MARKERS = re.compile(
    r"\b(BUILD FAILURE|BUILD FAILED|COMPILATION ERROR)\b",
    re.IGNORECASE,
)
_WARNING_RE = re.compile(rf"{_JAVAC_WARNING_RE.pattern}|{_BRACKET_WARNING_RE.pattern}", re.IGNORECASE)
_ERROR_RE = re.compile(rf"{_JAVAC_ERROR_RE.pattern}|{_BRACKET_ERROR_RE.pattern}", re.IGNORECASE)

_JAR_SUFFIX = ".jar"


def analyze_build(ctx: AnalyzerContext) -> AnalyzerResult:
    project = ctx.config["project"]
    language = project.get("language", "cpp")
    build_cmd = project.get("build_command", "")
    tool = _tool_name(build_cmd)
    if resolve_command(build_cmd, ctx.repo_root) is None:
        ctx.set_tool_version(tool, STATUS_SKIPPED)
        return AnalyzerResult(
            "build",
            STATUS_SKIPPED,
            {"status": "UNKNOWN", "note": f"build tool not found for: {build_cmd or '(none)'}"},
        )

    started = time.perf_counter()
    status = "SUCCESS"
    warn_count = 0
    err_count = 0

    result = run_command(build_cmd, ctx.repo_root)
    duration_ms = int((time.perf_counter() - started) * 1000)
    if result.returncode != 0:
        status = "FAILURE"
    warn_count, err_count = _count_output(result.stdout + result.stderr)
    if status == "SUCCESS" and _FAILURE_MARKERS.search((result.stdout + result.stderr).replace("\ufeff", "")):
        status = "FAILURE"

    binary_path = project.get("binary_path")
    artifact_paths = _artifact_paths(ctx.repo_root, binary_path, language)
    binary_size = None
    if artifact_paths:
        binary_size = _size_of(ctx.repo_root, artifact_paths[0])

    req = {
        "status": status,
        "duration_ms": duration_ms,
        "returncode": result.returncode,
        "compiler_warnings": warn_count,
        "compiler_errors": err_count,
        "start_time": utcnow_iso(),
        "end_time": utcnow_iso(),
        "metrics": {
            "binary_size": binary_size,
            "binary_size_change": None,
            "pct_binary_growth": None,
            "artifact_count": len(artifact_paths),
            "artifact_paths": artifact_paths,
        },
    }
    ctx.report["build"].update({k: v for k, v in req.items() if k not in ("metrics",)})
    ctx.report["metrics"].update(req["metrics"])
    ctx.set_tool_version(tool, STATUS_OK)
    return AnalyzerResult("build", STATUS_OK, req)


def _tool_name(build_cmd: str) -> str:
    tokens = (build_cmd or "").split()
    if not tokens:
        return "build-tool"
    first = Path(tokens[0]).name.lower()
    if first in ("cmd", "sh", "bash", "call"):
        return "build-tool"
    return first


def _count_output(output: str) -> tuple[int, int]:
    """Count warning and error lines. A line is counted at most once."""
    text = (output or "").replace("\ufeff", "")
    warn = err = 0
    for line in text.splitlines():
        if _ERROR_RE.search(line):
            err += 1
        elif _WARNING_RE.search(line):
            warn += 1
    return warn, err


def _artifact_paths(repo_root: Path, binary_path: str | None, language: str) -> list[str]:
    if binary_path:
        binary = (repo_root / binary_path).resolve()
        if binary.exists():
            return [binary_path]
        return []
    if language != "java":
        return []
    for jar in sorted(repo_root.rglob("*.jar")):
        if "test" not in jar.parts and "junit" not in jar.name:
            return [str(jar.relative_to(repo_root)).replace("\\", "/")]
    return []


def _size_of(repo_root: Path, rel_path: str) -> int | None:
    try:
        path = (repo_root / rel_path).resolve()
        return path.stat().st_size if path.exists() else None
    except OSError:
        return None