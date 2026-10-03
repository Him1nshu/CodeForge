"""Analyzer registry."""

from __future__ import annotations

from codeforge.analyzers import architecture, benchmarks, build, complexity, dependencies, git, static_analysis, tests
from codeforge.analyzers.base import Analyzer, AnalyzerContext

REGISTRY: dict[str, Analyzer] = {
    "git": git.analyze_git,
    "build": build.analyze_build,
    "tests": tests.analyze_tests,
    "static_analysis": static_analysis.analyze_static_analysis,
    "complexity": complexity.analyze_complexity,
    "benchmarks": benchmarks.analyze_benchmarks,
    "dependencies": dependencies.analyze_dependencies,
    "architecture": architecture.analyze_architecture,
}

ORDER = [
    "git",
    "build",
    "tests",
    "static_analysis",
    "complexity",
    "benchmarks",
    "dependencies",
    "architecture",
]


def run_all(ctx: AnalyzerContext, skip: set[str] | None = None) -> list:
    skip = skip or set()
    results = []
    for name in ORDER:
        if name in skip:
            continue
        results.append(REGISTRY[name](ctx))
    return results