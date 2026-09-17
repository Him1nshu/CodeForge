"""Architecture dependency-graph analyzer.

Pure Python. For C/C++ scans `#include "..."`; for Java scans
`import a.b.C;` (skipping JDK packages). Resolves the module of the including
file and the referenced header/package via the configured layer directory
prefixes, emitting directed module edges for the drift engine.
"""

from __future__ import annotations

import re
from pathlib import Path

from codeforge.analyzers.base import STATUS_OK, AnalyzerContext, AnalyzerResult

_CXX_SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx", ".c", ".hpp", ".hh", ".h"}
_JAVA_SOURCE_SUFFIXES = {".java"}
_INCLUDE_RE = re.compile(r'^#include\s+"([^"]+)"', re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*import\s+static\s+(?P<imp>[\w.]+)\s*;|^\s*import\s+(?P<pkg>[\w.]+)\s*;", re.MULTILINE)
_JDK_PREFIXES = ("java.", "javax.", "jdk.", "sun.", "com.sun.")
_JAVA_SOURCE_ROOTS = ("src/main/java", "src/test/java", "src/java", "src", "java")


def _source_files(repo_root: Path, suffixes: set[str]) -> list[Path]:
    return sorted(
        p for p in repo_root.rglob("*")
        if p.is_file() and p.suffix in suffixes and "build" not in p.parts
    )


def _module_of(relative: str, layer_prefixes: dict[str, list[str]]) -> str | None:
    for layer, prefixes in layer_prefixes.items():
        for prefix in prefixes:
            prefix = prefix.rstrip("/")
            if relative == prefix or relative.startswith(prefix + "/"):
                return layer
    first = relative.split("/")[0]
    return first if first and first not in ("..", ".") else None


def _resolve_header(repo_root: Path, including_file: Path, include: str) -> Path | None:
    candidates = [
        including_file.parent / include,
        repo_root / include,
    ]
    for cand in candidates:
        if cand.is_file():
            return cand.resolve()
    return None


def _resolve_import_dir(repo_root: Path, package: str) -> Path | None:
    """Find the source directory backing a package import, if internal."""
    pkg_path = package.replace(".", "/")
    for root in _JAVA_SOURCE_ROOTS:
        for candidate in (repo_root / root / pkg_path, repo_root / root / f"{package.rsplit('.', 1)[0].replace('.', '/')}"):
            if candidate.is_dir():
                return candidate
    return None


def _cxx_edges(repo_root: Path, layers: dict[str, list[str]], include_dirs: list[Path]) -> tuple[set[str], set[tuple[str, str]]]:
    modules: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for source in _source_files(repo_root, _CXX_SOURCE_SUFFIXES):
        relative = source.relative_to(repo_root).as_posix()
        src_module = _module_of(relative, layers) or "misc"
        modules.add(src_module)
        text = source.read_text(encoding="utf-8", errors="replace")
        for include in _INCLUDE_RE.findall(text):
            header = _resolve_header(repo_root, source, include)
            if header is None:
                for include_dir in include_dirs:
                    probe = include_dir / include
                    if probe.is_file():
                        header = probe
                        break
            if header is None:
                continue
            header_rel = header.relative_to(repo_root).as_posix()
            tgt_module = _module_of(header_rel, layers) or src_module
            modules.add(tgt_module)
            if src_module != tgt_module:
                edges.add((src_module, tgt_module))
    return modules, edges


def _java_edges(repo_root: Path, layers: dict[str, list[str]]) -> tuple[set[str], set[tuple[str, str]]]:
    modules: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for source in _source_files(repo_root, _JAVA_SOURCE_SUFFIXES):
        relative = source.relative_to(repo_root).as_posix()
        src_module = _module_of(relative, layers) or "misc"
        modules.add(src_module)
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in _IMPORT_RE.finditer(text):
            package = match.group("pkg") or match.group("imp")
            if not package or package.startswith(_JDK_PREFIXES):
                continue
            import_dir = _resolve_import_dir(repo_root, package)
            if import_dir is None:
                continue
            import_rel = import_dir.relative_to(repo_root).as_posix()
            tgt_module = _module_of(import_rel, layers) or src_module
            modules.add(tgt_module)
            if src_module != tgt_module:
                edges.add((src_module, tgt_module))
    return modules, edges


def analyze_architecture(ctx: AnalyzerContext) -> AnalyzerResult:
    layers = ctx.config["analyzers"].get("architecture", {}).get("layers", {})
    layer_mapping: dict[str, str] = {}
    for layer, prefixes in layers.items():
        for prefix in prefixes:
            layer_mapping[prefix.rstrip("/")] = layer

    language = ctx.config["project"].get("language", "cpp")
    include_dirs = [ctx.repo_root / "include", ctx.repo_root / "src"]
    if language == "java":
        modules, edges = _java_edges(ctx.repo_root, layers)
    else:
        modules, edges = _cxx_edges(ctx.repo_root, layers, include_dirs)

    report = {
        "module_count": len(modules),
        "edge_count": len(edges),
        "edges": [{"source": s, "target": t} for s, t in sorted(edges)],
        "layer_mapping": layer_mapping,
    }
    ctx.report["architecture"] = report
    ctx.set_tool_version("architecture", "internal")
    return AnalyzerResult("architecture", STATUS_OK, report)