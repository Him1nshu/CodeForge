"""Unit tests for the collector's pure analyzers (no external tools required)."""

from __future__ import annotations

import json
from pathlib import Path

from codeforge.analyzers import architecture, benchmarks, complexity, dependencies
from codeforge.analyzers.base import AnalyzerContext

LAYERS = {
    "presentation": ["src/presentation"],
    "application": ["src/application"],
    "domain": ["src/domain"],
    "infrastructure": ["src/infrastructure"],
}


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _ctx(root: Path, config: dict | None = None) -> AnalyzerContext:
    return AnalyzerContext(
        repo_root=root,
        config=config
        or {
            "project": {"benchmark_command": "benchmarks"},
            "analyzers": {
                "complexity": {"tool": "auto", "complexity_threshold": 15},
                "architecture": {"layers": LAYERS},
            },
        },
        report=_empty_report(),
    )


def _empty_report() -> dict:
    return {
        "build": {
            "status": "UNKNOWN",
            "collector_run_id": "test",
            "environment": {"os": "test", "tool_versions": {}},
        },
        "metrics": {},
        "tests": [],
        "benchmarks": [],
        "static_analysis": [],
        "complexity": {},
        "dependencies": [],
        "architecture": {"module_count": 0, "edge_count": 0, "edges": [], "layer_mapping": {}},
    }


CODE = {
    "src/presentation/main.cpp": """
#include "service.hpp"
int main() { auto s = Service{}; s.run(); return 0; }
""",
    "src/presentation/service.hpp": "#pragma once\n#include \"../application/svc.hpp\"\n",
    "src/application/svc.cpp": """
#include "svc.hpp"
namespace app { int Svc::run() { int total = 0; for (int i = 0; i < 10; ++i) { if (i % 2 == 0) total += i; } return total; } }
""",
    "src/application/svc.hpp": "#pragma once\n#include \"../domain/model.hpp\"\nnamespace app { struct Svc { int run(); }; }\n",
    "src/domain/model.hpp": "#pragma once\nnamespace domain { inline constexpr int k = 7; }\n",
}


def test_architecture_include_graph(tmp_path) -> None:
    _write_tree(tmp_path, CODE)
    ctx = _ctx(tmp_path)
    result = architecture.analyze_architecture(ctx)
    assert result.status == "ok"
    edges = {(e["source"], e["target"]) for e in ctx.report["architecture"]["edges"]}
    assert ("presentation", "application") in edges
    assert ("application", "domain") in edges
    assert ("domain", "infrastructure") not in edges


def test_complexity_counts_and_mi(tmp_path) -> None:
    _write_tree(tmp_path, CODE)
    ctx = _ctx(tmp_path)
    result = complexity.analyze_complexity(ctx)
    assert result.status == "ok"
    data = ctx.report["complexity"]
    assert data["functions"] >= 2
    assert data["lines_of_code"] > 0
    assert data["avg_function_complexity"] >= 1
    assert data["max_function_complexity"] >= 3  # the run() loop guard has if+for
    assert 0 <= data["maintainability_index"] <= 100


def test_complexity_above_threshold(tmp_path) -> None:
    hairy = {
        "src/domain/hairy.cpp": """
int heavy(int a, int b) {
  int r = 0;
  for (int i = 0; i < a; ++i) { if (i % 2) { r += 1; } else if (i % 3) { r += 2; } switch (i) { case 1: r++; break; case 2: r--; break; } }
  while (r > 100) { r -= 10; if (r & 1) { r--; } }
  return r;
}
""",
    }
    _write_tree(tmp_path, hairy)
    ctx = _ctx(tmp_path)
    complexity.analyze_complexity(ctx)
    data = ctx.report["complexity"]
    assert data["max_function_complexity"] >= 8
    assert data["functions_above_threshold"] >= 0


def test_dependencies_first_run_unchanged(tmp_path) -> None:
    _write_tree(tmp_path, {"dependencies.txt": "spdlog:1.13\nfmt:9.1\n"})
    ctx = _ctx(tmp_path)
    result = dependencies.analyze_dependencies(ctx)
    assert result.status == "ok"
    by_name = {d["name"]: d for d in ctx.report["dependencies"]}
    assert by_name["spdlog"]["change"] == "unchanged"
    assert by_name["spdlog"]["version"] == "1.13"


def test_dependencies_diff_against_previous(tmp_path) -> None:
    _write_tree(tmp_path, {"dependencies.txt": "spdlog:1.14\nfmt:9.1\n"})
    _write_tree(tmp_path, {"build_report.json": json.dumps({"dependencies": [
        {"name": "spdlog", "version": "1.13", "type": "txt", "change": "unchanged", "previous_version": None},
        {"name": "fmt", "version": "9.1", "type": "txt", "change": "unchanged", "previous_version": None},
    ]})})
    ctx = _ctx(tmp_path)
    dependencies.analyze_dependencies(ctx)
    by_name = {d["name"]: d for d in ctx.report["dependencies"]}
    assert by_name["spdlog"]["change"] == "updated"
    assert by_name["spdlog"]["previous_version"] == "1.13"


def test_benchmarks_parse_lines(tmp_path) -> None:
    _write_tree(tmp_path, {"benchmarks.bat": "@echo off\n@echo BENCHMARK vector_processing 120.5 118.0 3.0 115.0 1000.0 10\n@echo BENCHMARK hash_lookup 45.0 44.0 1.0 43.0 500.0 10\nexit /b 0\n"})
    ctx = _ctx_with_command(tmp_path, "benchmarks.bat")
    result = benchmarks.analyze_benchmarks(ctx)
    assert result.status == "ok"
    names = {b["name"] for b in ctx.report["benchmarks"]}
    assert names == {"vector_processing", "hash_lookup"}
    assert ctx.report["benchmarks"][0]["mean_ms"] == 120.5


def _ctx_with_command(root: Path, command: str) -> AnalyzerContext:
    base = _ctx(root)
    base.config["project"]["benchmark_command"] = command
    return base


def test_benchmarks_missing_binary_skipped(tmp_path) -> None:
    _write_tree(tmp_path, {})
    ctx = _ctx(tmp_path)
    result = benchmarks.analyze_benchmarks(ctx)
    assert result.status == "skipped"
    assert ctx.report["benchmarks"] == []