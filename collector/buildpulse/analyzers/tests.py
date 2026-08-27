"""Test runner + result parsing.

Modes (project.test_format):
- ctest:  parse ctest's "Test #n: name  Passed|Failed|Skipped" summary lines.
- junit:  after running test_command, merge JUnit XML (Surefire/Gradle/JUnit
          console `--reports-dir`) into per-test entries. Failure messages and
          stack traces are captured in the `error` field so the dashboard can
          tell exactly why a test failed.
- auto:   choose by the test command (ctest -> ctest, console ``--reports-dir``
          or Maven/Gradle -> junit), defaulting to ctest-style lines.
- none:   skip test collection.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from buildpulse.analyzers.base import (
    STATUS_OK,
    STATUS_SKIPPED,
    AnalyzerContext,
    AnalyzerResult,
    resolve_command,
    run_command,
)

_CTEST_LINE = re.compile(
    r"^\s*(?:\d+/\d+\s+)?(?:Test\s*#?\d*:?\s+)?(?P<name>\S+).*?\b(?P<result>Not Run|Passed|Failed|Skipped)\b.*$",
    re.MULTILINE | re.IGNORECASE,
)

_DEFAULT_JUNIT_DIRS = (
    "target/surefire-reports",
    "build/test-results/test",
    "build/reports/junitXml",
    "build/test-results",
    "test-results",
)


def analyze_tests(ctx: AnalyzerContext) -> AnalyzerResult:
    project = ctx.config["project"]
    test_command = project.get("test_command", "")
    if resolve_command(test_command, ctx.repo_root) is None:
        ctx.set_tool_version("test-runner", STATUS_SKIPPED)
        return AnalyzerResult("tests", STATUS_SKIPPED, {"tests": []})

    result = run_command(test_command, ctx.repo_root)
    output = (result.stdout + result.stderr).replace("\ufeff", "")
    fmt = _detect_format(project, test_command, ctx.repo_root)
    notes: list[str] = []
    if result.returncode != 0:
        notes.append(f"test_command exited {result.returncode}")

    tests: list[dict] = []
    if fmt == "none":
        ctx.report["tests"] = tests
        ctx.set_tool_version("test-runner", STATUS_SKIPPED)
        return AnalyzerResult("tests", STATUS_SKIPPED, {"tests": [], "note": "test_format=none"})
    if fmt == "junit":
        entries = _parse_junit_xml(ctx.repo_root, project.get("junit_reports_dir"))
        if entries is None:
            notes.append("no JUnit XML reports found after test run")
        elif not entries:
            notes.append("JUnit XML reports contained no testcases")
        if entries:
            tests = _dedupe(entries)
    else:
        for match in _CTEST_LINE.finditer(output):
            raw = match.group("result").lower()
            status = {"passed": "passed", "failed": "failed", "skipped": "skipped", "not run": "skipped"}[raw]
            tests.append({"suite": "ctest", "name": match.group("name"), "status": status})

    ctx.report["tests"] = tests
    ctx.set_tool_version("test-runner", STATUS_OK)
    return AnalyzerResult("tests", STATUS_OK, {"tests": tests, "note": "; ".join(notes)})


def _detect_format(project: dict, test_command: str, repo_root: Path) -> str:
    configured = str(project.get("test_format", "auto")).lower()
    if configured not in ("auto", "ctest", "junit", "none"):
        configured = "auto"
    if configured == "none":
        return "none"
    if configured in ("ctest", "junit"):
        return configured
    tokens = (test_command or "").lower()
    if (repo_root / "pom.xml").is_file() or (repo_root / "build.gradle").is_file():
        return "junit"
    if (repo_root / "pom.xml.kts").is_file() or (repo_root / "build.gradle.kts").is_file():
        return "junit"
    if (
        "junit" in tokens
        or "--reports-dir" in tokens
        or "surefire" in tokens
        or "gradle" in tokens
        or "mvn" in tokens
    ):
        return "junit"
    if str(project.get("language", "cpp")).lower() == "java":
        return "junit"
    if "ctest" in tokens:
        return "ctest"
    return "ctest"


def _parse_junit_xml(repo_root: Path, configured_dir: str | None) -> list[dict] | None:
    dirs = []
    if configured_dir:
        dirs.append(repo_root / configured_dir)
    dirs += [repo_root / d for d in _DEFAULT_JUNIT_DIRS]
    xml_files: list[Path] = []
    seen: set[Path] = set()
    for d in dirs:
        if d.is_dir():
            for p in sorted(q for q in d.rglob("*.xml")):
                resolved = p.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    xml_files.append(p)
    if not xml_files:
        return None
    entries: list[dict] = []
    for path in xml_files:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        suite_name = root.get("name") or path.stem
        for tc in root.iter("testcase"):
            cls = tc.get("classname") or "".join(suite_name.split())
            name = tc.get("name") or "unknown"
            status = "passed"
            error = None
            for child in tc:
                tag = child.tag.lower()
                if tag in ("failure", "error"):
                    status = "failed"
                    message = child.get("message") or ""
                    body = (child.text or "").strip()
                    detail = message or body[:400] or f"{tag} (no detail)"
                    error = detail[:2000]
                    break
                if tag == "skipped":
                    status = "skipped"
            duration = _float(tc.get("time"))
            entries.append(
                {
                    "suite": suite_name or cls,
                    "name": f"{cls}.{name}" if cls and not name.startswith(cls) else name,
                    "status": status,
                    "duration_ms": duration,
                    "error": error,
                }
            )
    return entries


def _dedupe(entries: list[dict]) -> list[dict]:
    """Keep names unique within a (suite, name) so backend dedupe can't collide."""
    seen: dict[tuple[str, str], int] = {}
    out: list[dict] = []
    for entry in entries:
        key = (entry["suite"], entry["name"])
        hit = seen.get(key, 0)
        seen[key] = hit + 1
        if hit:
            entry = dict(entry)
            entry["name"] = f"{entry['name']}#{hit + 1}"
        out.append(entry)
    return out


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * 1000.0
    except ValueError:
        return None