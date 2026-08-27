"""Dependency manifest diffing against the previous collect report.

Sections analyzed: `dependencies.txt` (lines `name:version`) at repo root, or a
`conanfile.py`/`vcpkg.json` when present. Change detection is report-to-report
so a fresh CI checkout still gets `added/removed/updated` signals.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from buildpulse.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult
from buildpulse.report import load_last_report

_LINE = re.compile(r"^\s*([^:#\s]+)\s*:\s*([^\s]+)\s*$")
_GRADLE_DEP = re.compile(
    r"\b(?:implementation|api|compileOnly|runtimeOnly|testImplementation|classpath)\s*[\(\'\"]\s*([\w.\-]+):([\w.\-]+):([\w.\-]+)"
)


def _read_dependencies(repo_root: Path, language: str) -> list[dict] | None:
    candidates = [
        repo_root / "dependencies.txt",
        repo_root / "conanfile.txt",
        repo_root / "vcpkg.json",
    ]
    if language == "java":
        candidates += [
            repo_root / "pom.xml",
            repo_root / "build.gradle",
            repo_root / "build.gradle.kts",
        ]
    for path in candidates:
        if path.exists():
            deps: list[dict] = []
            if path.name == "vcpkg.json":
                try:
                    data = json.loads(path.read_text(encoding="utf-8-sig"))
                    for item in data.get("dependencies", []):
                        name = item if isinstance(item, str) else item.get("name")
                        version = item.get("version") if isinstance(item, dict) else None
                        if name:
                            deps.append({"name": name, "version": version, "type": "vcpkg"})
                    return deps
                except (ValueError, OSError):
                    return None
            if path.name == "pom.xml":
                parsed = _parse_pom(path)
                if parsed is not None:
                    return parsed or []
            if path.name.startswith("build.gradle"):
                parsed = _parse_gradle(path)
                if parsed is not None:
                    return parsed or []
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                match = _LINE.match(line)
                if match:
                    deps.append(
                        {"name": match.group(1), "version": match.group(2), "type": path.suffix.lstrip(".") or "txt"}
                    )
            return deps
    return None


def _parse_pom(path: Path) -> list[dict] | None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    parents: dict[ET.Element, ET.Element] = {}
    for element in root.iter():
        for child in element:
            parents[child] = element

    def _inside_build_or_plugin(element: ET.Element) -> bool:
        cursor = element
        while cursor in parents:
            if _local_name(cursor.tag) in ("build", "plugin", "plugins"):
                return True
            cursor = parents[cursor]
        return False

    deps: list[dict] = []
    for group in root.iter():
        if _local_name(group.tag) != "dependencies" or _inside_build_or_plugin(group):
            continue
        for dep in group:
            if _local_name(dep.tag) != "dependency":
                continue
            parsed = {
                _local_name(child.tag): (child.text or "").strip()
                for child in dep
                if _local_name(child.tag) in ("groupId", "artifactId", "version")
            }
            group_id = parsed.get("groupId")
            artifact = parsed.get("artifactId")
            if group_id and artifact:
                deps.append(
                    {
                        "name": f"{group_id}:{artifact}",
                        "version": parsed.get("version") or None,
                        "type": "maven",
                    }
                )
    return deps


def _parse_gradle(path: Path) -> list[dict] | None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    deps: list[dict] = []
    for match in _GRADLE_DEP.finditer(text):
        group, artifact, version = match.groups()
        deps.append({"name": f"{group}:{artifact}", "version": version, "type": "gradle"})
    return deps


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def analyze_dependencies(ctx: AnalyzerContext) -> AnalyzerResult:
    language = ctx.config["project"].get("language", "cpp")
    current = _read_dependencies(ctx.repo_root, language)
    if current is None:
        ctx.report["dependencies"] = []
        ctx.set_tool_version("dependencies", STATUS_SKIPPED)
        return AnalyzerResult("dependencies", STATUS_SKIPPED, {"dependencies": [], "note": "no manifest found"})

    previous_report = load_last_report(ctx.repo_root)
    previous = previous_report.get("dependencies", []) if previous_report else []

    prev_by_name = {dep["name"]: dep.get("version") for dep in previous}
    out: list[dict] = []
    for dep in current:
        name = dep["name"]
        old = prev_by_name.get(name)
        if prev_by_name and name not in prev_by_name:
            change = "added"
        elif prev_by_name and old != dep["version"]:
            change = "updated"
        else:
            change = "unchanged"
        out.append(
            {
                "name": name,
                "version": dep["version"],
                "type": dep["type"],
                "change": change,
                "previous_version": old,
            }
        )
    present_names = {d["name"] for d in current}
    for name, version in prev_by_name.items():
        if name not in present_names:
            out.append(
                {"name": name, "version": None, "type": "previous", "change": "removed", "previous_version": version}
            )

    ctx.report["dependencies"] = out
    ctx.set_tool_version("dependencies", STATUS_OK)
    return AnalyzerResult("dependencies", STATUS_OK, {"dependencies": out})