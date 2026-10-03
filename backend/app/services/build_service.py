"""Ingestion core: persist a collector BuildReport and run the derived
computation pipeline (health score, trends, insights) so that every stored
build is fully analysed at write time.

This service owns the DB writes; all scoring/trend/insight math lives in the
pure `app.intelligence` package.
"""

import logging
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.intelligence.drift import Edge, compute_drift
from app.intelligence.health_score import HealthInput, compute_health
from app.intelligence.insights import EngineInsight, InsightsContext, generate_insights
from app.intelligence.trends import (
    BenchmarkRegression,
    classify_benchmark_regression,
    classify_trend,
)
from app.models.analysis import (
    ArchitectureMetrics,
    ArchitectureViolation,
    BenchmarkResult,
    CodeMetrics,
    DependencyRecord,
    StaticAnalysisIssue,
    TestResult,
)
from app.models.build import Build, BuildMetrics
from app.models.health import EngineeringInsight, HealthScore
from app.models.project import Project
from app.schemas.build import BuildIngestResponse, BuildReport

logger = logging.getLogger("codeforge.services.build")

TEST_STATUSES = ("passed", "failed")


class DuplicateBuildError(Exception):
    def __init__(self, build_id: uuid.UUID) -> None:
        self.build_id = build_id


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _persist_analysis_rows(build: Build, report: BuildReport) -> None:
    """Create all per-build metric rows from the validated report."""
    if report.complexity:
        build.code_metrics = CodeMetrics(
            lines_of_code=report.complexity.lines_of_code,
            functions=report.complexity.functions,
            cyclomatic_complexity_total=report.complexity.cyclomatic_complexity_total,
            avg_function_complexity=report.complexity.avg_function_complexity,
            max_function_complexity=report.complexity.max_function_complexity,
            functions_above_threshold=report.complexity.functions_above_threshold,
            complexity_threshold=report.complexity.complexity_threshold,
            maintainability_index=report.complexity.maintainability_index,
            avg_function_length=report.complexity.avg_function_length,
            top_complex_functions=report.complexity.top_complex_functions,
        )

    for issue in report.static_analysis:
        build.issues.append(
            StaticAnalysisIssue(
                tool=issue.tool,
                file=issue.file,
                line=issue.line,
                severity=issue.severity.lower(),
                rule=issue.rule,
                message=issue.message,
                category=issue.category,
            )
        )

    for test in report.tests:
        build.test_results.append(
            TestResult(
                suite=test.suite,
                name=test.name,
                status=test.status.lower(),
                duration_ms=test.duration_ms,
                error_message=test.error,
            )
        )

    for bench in report.benchmarks:
        build.benchmarks.append(
            BenchmarkResult(
                name=bench.name,
                mean_ms=bench.mean_ms,
                median_ms=bench.median_ms,
                stddev_ms=bench.stddev_ms,
                cpu_ms=bench.cpu_ms,
                throughput=bench.throughput,
                iterations=bench.iterations,
            )
        )

    for dep in report.dependencies:
        build.dependencies.append(
            DependencyRecord(
                name=dep.name,
                version=dep.version,
                type=dep.type,
                change=dep.change,
                previous_version=dep.previous_version,
            )
        )

    # Architecture drift is derived here because it shapes stored violations.
    arch = report.architecture
    drift = compute_drift(
        edges=[Edge(source=e.source, target=e.target) for e in arch.edges],
        layer_mapping=arch.layer_mapping or None,
    )
    build.arch_metrics = ArchitectureMetrics(
        drift_score=drift.drift_score,
        layer_violations=drift.layer_violations,
        cyclic_dependencies=drift.cyclic_dependencies,
        unexpected_coupling=drift.unexpected_coupling,
        direction_violations=drift.direction_violations,
        module_count=drift.module_count,
        edge_count=drift.edge_count,
        dependency_graph=drift.graph,
    )
    for v in drift.violations:
        build.arch_violations.append(
            ArchitectureViolation(
                violation_type=v.violation_type,
                source_module=v.source_module,
                target_module=v.target_module,
                source_layer=v.source_layer,
                target_layer=v.target_layer,
                message=v.message,
            )
        )


def _history_data(db: Session, project_id: uuid.UUID, before_build_number: int) -> dict:
    """Raw per-metric series from all previous builds (ascending)."""
    builds = list(
        db.execute(
            select(Build)
            .where(Build.project_id == project_id, Build.build_number < before_build_number)
            .order_by(Build.build_number.asc())
        ).scalars()
    )
    series: dict[str, list[float]] = defaultdict(list)
    prev_issue_density: float | None = None
    prev_benchmarks: dict[str, float] = {}
    prev_functions_above: int | None = None
    previous_health: HealthScore | None = None

    latest = builds[-1] if builds else None
    if latest is not None:
        prev_issue_density = _issue_density(latest)
        if latest.code_metrics:
            prev_functions_above = latest.code_metrics.functions_above_threshold
        for b in latest.benchmarks:
            if b.mean_ms is not None:
                prev_benchmarks[b.name] = b.mean_ms
        previous_health = db.scalar(
            select(HealthScore).where(HealthScore.build_id == latest.id)
        )

    for b in builds:
        if b.duration_ms is not None:
            series["build_duration_ms"].append(float(b.duration_ms))
        if b.compiler_warnings:
            series["compiler_warnings"].append(float(b.compiler_warnings))
        if b.compiler_errors:
            series["compiler_errors"].append(float(b.compiler_errors))
        if b.metrics and b.metrics.binary_size is not None:
            series["binary_size_bytes"].append(float(b.metrics.binary_size))
        if b.issues:
            series["static_analysis_issues"].append(float(len(b.issues)))
        if b.code_metrics:
            if b.code_metrics.max_function_complexity is not None:
                series["max_function_complexity"].append(float(b.code_metrics.max_function_complexity))
            if b.code_metrics.avg_function_complexity is not None:
                series["avg_function_complexity"].append(float(b.code_metrics.avg_function_complexity))
            if b.code_metrics.functions_above_threshold is not None:
                series["functions_above_threshold"].append(float(b.code_metrics.functions_above_threshold))
            if b.code_metrics.maintainability_index is not None:
                series["maintainability_index"].append(float(b.code_metrics.maintainability_index))
        if b.test_results:
            passed = sum(1 for t in b.test_results if t.status == "passed")
            total = len(b.test_results)
            dur = sum((t.duration_ms or 0.0) for t in b.test_results)
            series["test_pass_rate"].append(passed / total)
            series["test_count"].append(float(total))
            series["mean_test_duration_ms"].append(dur / total)
        if b.arch_metrics:
            series["architecture_drift_score"].append(float(b.arch_metrics.drift_score))

    return {
        "series": series,
        "prev_issue_density": prev_issue_density,
        "prev_benchmarks": prev_benchmarks,
        "prev_functions_above": prev_functions_above,
        "previous_health": previous_health,
        "latest_previous_build": latest,
    }


def _issue_density(build: Build) -> float | None:
    if not build.code_metrics or not build.code_metrics.lines_of_code:
        return None
    weighted = sum(
        {
            "critical": 3,
            "high": 2,
            "medium": 1.5,
            "low": 1,
        }.get(i.severity, 1)
        for i in build.issues
    )
    return weighted / build.code_metrics.lines_of_code * 1000.0


def _flaky_tests(db: Session, project_id: uuid.UUID) -> list[str]:
    """Flag tests that change pass/fail state across >=2 transitions and >=3 runs."""
    rows = list(
        db.execute(
            select(Build.build_number, TestResult.name, TestResult.status)
            .join(TestResult, TestResult.build_id == Build.id)
            .where(Build.project_id == project_id, TestResult.status.in_(TEST_STATUSES))
            .order_by(Build.build_number.asc(), TestResult.name.asc())
        ).all()
    )
    series: dict[str, list[str]] = defaultdict(list)
    for _, name, status in rows:
        series[name].append(status)
    flaky: list[str] = []
    for name, statuses in series.items():
        changes = sum(1 for i in range(1, len(statuses)) if statuses[i] != statuses[i - 1])
        if len(statuses) >= 3 and changes >= 2:
            flaky.append(name)
    return sorted(flaky)


def _benchmark_pairs(build: Build, prev_benchmarks: dict[str, float]) -> list[tuple[float | None, float | None]]:
    pairs: list[tuple[float | None, float | None]] = []
    for b in build.benchmarks:
        pairs.append((prev_benchmarks.get(b.name), b.mean_ms))
    return pairs


def _test_counts(build: Build) -> tuple[int, int, int]:
    passed = sum(1 for t in build.test_results if t.status == "passed")
    failed = sum(1 for t in build.test_results if t.status == "failed")
    skipped = sum(1 for t in build.test_results if t.status == "skipped")
    return passed, failed, skipped


def _trends(history: dict, build: Build) -> list:
    """Full-series trend for the current build across all known metrics."""
    report = {}

    def push(metric: str, value: float | None) -> None:
        if value is None:
            return
        series = history["series"].get(metric, [])
        report[metric] = classify_trend(metric, [*series, value])

    push("build_duration_ms", float(build.duration_ms) if build.duration_ms is not None else None)
    push("compiler_warnings", float(build.compiler_warnings))
    push("compiler_errors", float(build.compiler_errors))
    if build.metrics and build.metrics.binary_size is not None:
        push("binary_size_bytes", float(build.metrics.binary_size))
    push("static_analysis_issues", float(len(build.issues)))
    if build.code_metrics:
        push("max_function_complexity", build.code_metrics.max_function_complexity)
        push("avg_function_complexity", build.code_metrics.avg_function_complexity)
        push("functions_above_threshold", build.code_metrics.functions_above_threshold)
        push("maintainability_index", build.code_metrics.maintainability_index)
    passed, _failed, _skipped = _test_counts(build)
    if build.test_results:
        total = len(build.test_results)
        push("test_pass_rate", passed / total)
        push("test_count", float(total))
        durations = [t.duration_ms or 0.0 for t in build.test_results]
        push("mean_test_duration_ms", sum(durations) / len(durations))
    if build.arch_metrics:
        push("architecture_drift_score", float(build.arch_metrics.drift_score))
    return list(report.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_build(
    db: Session,
    project: Project,
    report: BuildReport,
    max_issues: int = 20000,
) -> BuildIngestResponse:
    """Persist a validated report and run the full derived-computation pipeline."""

    if len(report.static_analysis) > max_issues:
        raise ValueError(f"report contains {len(report.static_analysis)} issues; limit is {max_issues}")

    # Dedupe on (commit_hash, collector_run_id) — CI retries must not double count.
    if report.build.commit_hash and report.build.collector_run_id:
        existing = db.scalar(
            select(Build).where(
                Build.project_id == project.id,
                Build.commit_hash == report.build.commit_hash,
                Build.collector_run_id == report.build.collector_run_id,
            )
        )
        if existing is not None:
            return BuildIngestResponse(
                build_id=existing.id,
                build_number=existing.build_number,
                health_score=existing.health.overall_score if existing.health else None,
                insights_created=0,
                duplicate=True,
                note="build already ingested",
            )

    next_number = (db.scalar(select(func.count(Build.id)).where(Build.project_id == project.id)) or 0) + 1
    # Race-safe-ish: recompute max and bump when retries occur.
    max_number = db.scalar(
        select(func.max(Build.build_number)).where(Build.project_id == project.id)
    )
    if max_number is not None and max_number >= next_number:
        next_number = max_number + 1

    rb = report.build
    build = Build(
        project_id=project.id,
        build_number=next_number,
        status=rb.status.upper(),
        start_time=rb.start_time,
        end_time=rb.end_time,
        duration_ms=rb.duration_ms,
        commit_hash=rb.commit_hash,
        branch=rb.branch,
        commit_message=rb.commit_message,
        commit_author=rb.commit_author,
        commit_timestamp=rb.commit_timestamp,
        changed_files=rb.changed_files,
        lines_added=rb.lines_added,
        lines_removed=rb.lines_removed,
        compiler_warnings=rb.compiler_warnings,
        compiler_errors=rb.compiler_errors,
        build_retries=rb.build_retries,
        collector_run_id=rb.collector_run_id,
        environment=rb.environment.model_dump() if rb.environment else {},
        raw_report=report.model_dump(mode="json"),
    )
    if rb.duration_ms is None and rb.start_time and rb.end_time:
        build.duration_ms = int((rb.end_time - rb.start_time).total_seconds() * 1000)

    m = report.metrics
    if m.binary_size is not None or m.artifact_count is not None:
        build.metrics = BuildMetrics(
            binary_size=m.binary_size,
            binary_size_change=m.binary_size_change,
            pct_binary_growth=m.pct_binary_growth,
            artifact_count=m.artifact_count,
            artifact_paths=m.artifact_paths,
        )

    db.add(build)
    db.flush()
    _persist_analysis_rows(build, report)
    db.flush()

    # ---- derived pipeline -------------------------------------------------
    history = _history_data(db, project.id, next_number)

    severity_counts: dict[str, int] = defaultdict(int)
    for issue in build.issues:
        severity_counts[issue.severity] += 1

    passed, failed, skipped = _test_counts(build)
    flaky = _flaky_tests(db, project.id)

    weights = (project.health_config or {}).get("weights")
    health_input = HealthInput(
        status=build.status,
        duration_ms=build.duration_ms,
        durations_history=history["series"].get("build_duration_ms", [])[-4:],
        compiler_warnings=build.compiler_warnings,
        issue_severity_counts=dict(severity_counts),
        lines_of_code=build.code_metrics.lines_of_code if build.code_metrics else None,
        previous_issue_density=history["prev_issue_density"],
        passed=passed,
        failed=failed,
        skipped=skipped,
        flaky_count=len(flaky),
        benchmark_pairs=_benchmark_pairs(build, history["prev_benchmarks"]),
        maintainability_index=build.code_metrics.maintainability_index if build.code_metrics else None,
        functions_above_threshold=build.code_metrics.functions_above_threshold if build.code_metrics else None,
        avg_function_complexity=build.code_metrics.avg_function_complexity if build.code_metrics else None,
        drift_score=build.arch_metrics.drift_score if build.arch_metrics else None,
        weights=weights,
    )
    health = compute_health(health_input)

    health_row = HealthScore(
        build_id=build.id,
        project_id=project.id,
        overall_score=health.overall_score,
        build_health=health.build_health,
        code_quality=health.code_quality,
        testing=health.testing,
        performance=health.performance,
        maintainability=health.maintainability,
        architecture=health.architecture,
        grade=health.grade,
        formula_version=health.formula_version,
        weights=health.weights,
        evidence=health.evidence,
    )
    db.add(health_row)

    trends = _trends(history, build)

    benchmark_regressions: list[BenchmarkRegression] = []
    for b in build.benchmarks:
        r = classify_benchmark_regression(
            b.name, history["prev_benchmarks"].get(b.name), b.mean_ms
        )
        if r and r.severity != "OK":
            benchmark_regressions.append(r)

    deps_added = sum(1 for d in build.dependencies if d.change == "added")
    deps_removed = sum(1 for d in build.dependencies if d.change == "removed")
    deps_updated = sum(1 for d in build.dependencies if d.change == "updated")

    ctx = InsightsContext(
        build_number=build.build_number,
        health=health,
        previous_health=history["previous_health"],
        status=build.status,
        trends=trends,
        passed=passed,
        failed=failed,
        skipped=skipped,
        flaky_tests=flaky,
        benchmark_regressions=benchmark_regressions,
        deps_added=deps_added,
        deps_removed=deps_removed,
        deps_updated=deps_updated,
        functions_above_threshold=build.code_metrics.functions_above_threshold if build.code_metrics else None,
        previous_functions_above_threshold=history["prev_functions_above"],
        drift_score=build.arch_metrics.drift_score if build.arch_metrics else None,
    )
    insights: list[EngineInsight] = generate_insights(ctx)
    for insight in insights:
        db.add(
            EngineeringInsight(
                build_id=build.id,
                project_id=project.id,
                priority=insight.priority,
                category=insight.category,
                title=insight.title,
                message=insight.message,
                recommendation=insight.recommendation,
                evidence=insight.evidence,
            )
        )

    db.commit()
    db.refresh(build)
    logger.info("ingested build %s for project %s (health %.1f)", build.id, project.id, health.overall_score)
    return BuildIngestResponse(
        build_id=build.id,
        build_number=build.build_number,
        health_score=health.overall_score,
        insights_created=len(insights),
        duplicate=False,
    )
