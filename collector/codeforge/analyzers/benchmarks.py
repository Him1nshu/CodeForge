"""Benchmark harness runner.

Expects the benchmark binary/prefixed tool to print, for each benchmark:

    BENCHMARK <name> <mean_ms> <median_ms> <stddev_ms> <cpu_ms> <throughput> <iterations>
"""

from __future__ import annotations

import re
import shutil

from codeforge.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult, run_command

_LINE = re.compile(
    r"^BENCHMARK\s+(\S+)\s+([\d.]+|-)\s+([\d.]+|-)\s+([\d.]+|-)\s+([\d.]+|-)\s+([\d.]+|-)\s+(\d+|-)\s*$",
    re.MULTILINE,
)


def analyze_benchmarks(ctx: AnalyzerContext) -> AnalyzerResult:
    project = ctx.config["project"]
    cmd = project.get("benchmark_command")
    if not cmd:
        ctx.report["benchmarks"] = []
        ctx.set_tool_version("benchmark", STATUS_SKIPPED)
        return AnalyzerResult("benchmarks", STATUS_SKIPPED, {"benchmarks": [], "note": "no benchmark_command"})

    exe = cmd.split()[0]
    resolved = (ctx.repo_root / exe).resolve()
    if not resolved.exists() and shutil.which(exe) is None:
        ctx.report["benchmarks"] = []
        ctx.set_tool_version("benchmark", STATUS_SKIPPED)
        return AnalyzerResult("benchmarks", STATUS_SKIPPED, {"benchmarks": [], "note": f"benchmark binary {exe} missing"})

    result = run_command(cmd, ctx.repo_root)
    benchmarks: list[dict] = []
    for match in _LINE.finditer(result.stdout):
        values = [match.group(i) for i in range(2, 8)]
        benchmarks.append(
            {
                "name": match.group(1),
                "mean_ms": _num(values[0]),
                "median_ms": _num(values[1]),
                "stddev_ms": _num(values[2]),
                "cpu_ms": _num(values[3]),
                "throughput": _num(values[4]),
                "iterations": _num(values[5]),
            }
        )
    ctx.report["benchmarks"] = benchmarks
    ctx.set_tool_version("benchmark", STATUS_OK)
    return AnalyzerResult("benchmarks", STATUS_OK, {"benchmarks": benchmarks})


def _num(value: str) -> float | None:
    if value == "-":
        return None
    try:
        return float(value)
    except ValueError:
        return None