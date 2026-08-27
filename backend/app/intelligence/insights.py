"""Rule-based Engineering Insights engine (pure).

Consumes structured metrics + trend results and emits prioritized, actionable
insights. Insights always cite the numbers they are based on; the engine never
invents data. Rules are intentionally simple and auditable, one per concern.
"""

from dataclasses import dataclass, field

from app.intelligence.health_score import HealthResult
from app.intelligence.trends import BenchmarkRegression, TrendResult

PRIORITY_RANK = {"info": 0, "warning": 1, "high": 2, "critical": 3}


@dataclass
class EngineInsight:
    priority: str
    category: str
    title: str
    message: str
    recommendation: str
    evidence: dict = field(default_factory=dict)


@dataclass
class InsightsContext:
    build_number: int
    health: HealthResult | None = None
    previous_health: HealthResult | None = None
    status: str = "UNKNOWN"
    trends: list[TrendResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    flaky_tests: list[str] = field(default_factory=list)
    benchmark_regressions: list[BenchmarkRegression] = field(default_factory=list)
    deps_added: int = 0
    deps_removed: int = 0
    deps_updated: int = 0
    functions_above_threshold: int | None = None
    previous_functions_above_threshold: int | None = None
    drift_score: float | None = None


def _trend_of(ctx: InsightsContext, metric: str) -> TrendResult | None:
    for t in ctx.trends:
        if t.metric == metric:
            return t
    return None


def generate_insights(ctx: InsightsContext) -> list[EngineInsight]:
    out: list[EngineInsight] = []

    # 1. Build status
    if ctx.status not in ("SUCCESS", "PASSED"):
        out.append(
            EngineInsight(
                priority="critical",
                category="build",
                title=f"Build {ctx.build_number} failed",
                message=f"Build status is {ctx.status}: the software has no runnable artifact.",
                recommendation="Inspect the build log, fix compile/link errors, and re-run the collector.",
                evidence={"status": ctx.status},
            )
        )

    # 2. Build duration trend
    t = _trend_of(ctx, "build_duration_ms")
    if t and t.change_percent and t.change_percent >= 10:
        p = "critical" if t.direction == "CRITICAL" else ("high" if t.change_percent >= 25 else "warning")
        out.append(
            EngineInsight(
                priority=p,
                category="build",
                title="Build time is increasing",
                message=f"Build duration changed {t.change_percent:+.1f}% "
                        f"(current {t.current:.0f} ms).",
                recommendation="Investigate recently modified modules, dependency expansion, and compiler cache effectiveness.",
                evidence={"metric": "build_duration_ms", "current": t.current, "change_percent": t.change_percent},
            )
        )

    # 3. Compiler warnings
    t = _trend_of(ctx, "compiler_warnings")
    if t and t.change_percent and t.change_percent >= 50:
        out.append(
            EngineInsight(
                priority="warning",
                category="code_quality",
                title="Compiler warnings increased significantly",
                message=f"Compiler warnings rose by {t.change_percent:+.0f}% "
                        f"to {t.current:.0f} in build {ctx.build_number}.",
                recommendation="Enable -Wall/-Werror locally and fix warnings at the source.",
                evidence={"metric": "compiler_warnings", "current": t.current, "change_percent": t.change_percent},
            )
        )

    # 4. Static analysis issues
    t = _trend_of(ctx, "static_analysis_issues")
    if t and t.change_percent and t.change_percent >= 30:
        p = "critical" if t.change_percent >= 60 else ("high" if t.change_percent >= 45 else "warning")
        out.append(
            EngineInsight(
                priority=p,
                category="code_quality",
                title="Static analysis issues are accumulating",
                message=f"Issue count changed {t.change_percent:+.0f}% (now {t.current:.0f}).",
                recommendation="Prioritize critical/high severity issues; add rules to CI to cap the count.",
                evidence={"metric": "static_analysis_issues", "current": t.current, "change_percent": t.change_percent},
            )
        )

    # 5. Complexity growth
    if (
        ctx.functions_above_threshold is not None
        and ctx.previous_functions_above_threshold is not None
        and ctx.functions_above_threshold > ctx.previous_functions_above_threshold
    ):
        out.append(
            EngineInsight(
                priority="high",
                category="maintainability",
                title="Code complexity is increasing",
                message=(
                    f"Functions above the complexity threshold grew from "
                    f"{ctx.previous_functions_above_threshold} to {ctx.functions_above_threshold}."
                ),
                recommendation="Refactor high-complexity functions first; check the significant-change approach "
                               "(e.g. Linux kernel) for borderline cases.",
                evidence={
                    "prev_functions_above_threshold": ctx.previous_functions_above_threshold,
                    "functions_above_threshold": ctx.functions_above_threshold,
                },
            )
        )

    # 6. Test failures
    if ctx.failed > 0:
        out.append(
            EngineInsight(
                priority="critical" if ctx.failed >= 3 else "high",
                category="testing",
                title=f"{ctx.failed} test(s) failing",
                message=f"Build {ctx.build_number}: {ctx.failed} failed, {ctx.passed} passed, {ctx.skipped} skipped.",
                recommendation="Fix the failing tests before adding features; check for shared state and ordering issues.",
                evidence={"failed": ctx.failed, "passed": ctx.passed, "skipped": ctx.skipped},
            )
        )

    # 7. Flaky tests
    if ctx.flaky_tests:
        out.append(
            EngineInsight(
                priority="warning",
                category="testing",
                title="Potentially flaky tests detected",
                message=f"{len(ctx.flaky_tests)} test(s) flapped between builds: {', '.join(ctx.flaky_tests[:5])}.",
                recommendation="Quarantine flaky tests and eliminate global state, time dependence, and network calls.",
                evidence={"flaky_tests": ctx.flaky_tests[:10]},
            )
        )

    # 8. Benchmark regressions
    for r in ctx.benchmark_regressions:
        if r.severity == "OK":
            continue
        p = "critical" if r.severity == "CRITICAL" else "high"
        out.append(
            EngineInsight(
                priority=p,
                category="performance",
                title=f"Benchmark regression: {r.name}",
                message=f"{r.name}: {r.previous_ms} ms → {r.current_ms} ms ({r.change_percent:+.1f}%).",
                recommendation="Profile the regression (perf/valgrind), bisect the commit, and revert or fix the hot path.",
                evidence={"benchmark": r.name, "previous_ms": r.previous_ms, "current_ms": r.current_ms, "change_percent": r.change_percent},
            )
        )

    # 9. Dependency churn
    if ctx.deps_added + ctx.deps_removed + ctx.deps_updated > 0:
        out.append(
            EngineInsight(
                priority="info",
                category="dependencies",
                title="Dependency churn",
                message=f"Build {ctx.build_number}: {ctx.deps_added} added, {ctx.deps_removed} removed, "
                        f"{ctx.deps_updated} updated.",
                recommendation="Review new dependencies for supply-chain risk and license obligations.",
                evidence={"added": ctx.deps_added, "removed": ctx.deps_removed, "updated": ctx.deps_updated},
            )
        )

    # 10. Architecture drift
    if ctx.drift_score is not None and ctx.drift_score >= 15:
        p = "critical" if ctx.drift_score >= 60 else ("high" if ctx.drift_score >= 35 else "warning")
        out.append(
            EngineInsight(
                priority=p,
                category="architecture",
                title="Architecture drift detected",
                message=f"Drift score is {ctx.drift_score:.0f}/100 — layer/dependency rules are being violated.",
                recommendation="Fix layer violations and dependency cycles; see the Architecture Intelligence page for edges.",
                evidence={"drift_score": ctx.drift_score},
            )
        )

    # 11. Large health-score drops
    if ctx.health is not None and ctx.previous_health is not None:
        drop = ctx.previous_health.overall_score - ctx.health.overall_score
        if drop >= 15:
            out.append(
                EngineInsight(
                    priority="critical",
                    category="health",
                    title="Engineering Health Score collapsed",
                    message=f"Health dropped {drop:.1f} points ({ctx.previous_health.overall_score:.1f} → "
                            f"{ctx.health.overall_score:.1f}).",
                    recommendation="Review the categories that dropped most in this build; cross-check trend anomalies.",
                    evidence={"previous": ctx.previous_health.overall_score, "current": ctx.health.overall_score},
                )
            )
        elif drop >= 8:
            out.append(
                EngineInsight(
                    priority="high",
                    category="health",
                    title="Engineering Health Score declining",
                    message=f"Health dropped {drop:.1f} points since the previous build.",
                    recommendation="Inspect the categories flagged in the health detail before the next release.",
                    evidence={"previous": ctx.previous_health.overall_score, "current": ctx.health.overall_score},
                )
            )

    # 12. Healthy fallback
    if not out and ctx.health is not None:
        out.append(
            EngineInsight(
                priority="info",
                category="health",
                title="No significant degradation detected",
                message=f"Build {ctx.build_number} scored {ctx.health.overall_score:.1f}/100 with no "
                        "regressions above the configured thresholds.",
                recommendation="Continue monitoring; no action required.",
                evidence={"health_score": ctx.health.overall_score},
            )
        )

    out.sort(key=lambda i: -PRIORITY_RANK[i.priority])
    return out
