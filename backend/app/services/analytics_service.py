"""Read-side analytics service: serves every dashboard endpoint from stored raw
data. Trend/scoring values for display are recomputed on the fly from stored
series so the dashboard always reflects current logic without extra writers."""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.intelligence.trends import DIRECTION_FOR_METRIC, classify_trend
from app.models.analysis import (
    ArchitectureMetrics,
    ArchitectureViolation,
    BenchmarkResult,
    TestResult,
)
from app.models.build import Build
from app.models.health import EngineeringInsight, HealthScore
from app.schemas.build import BuildSummary


def latest_build(db: Session, project_id: uuid.UUID) -> Build | None:
    return db.scalar(
        select(Build)
        .where(Build.project_id == project_id)
        .order_by(Build.build_number.desc())
        .limit(1)
    )


def latest_health(db: Session, project_id: uuid.UUID) -> HealthScore | None:
    return db.scalar(
        select(HealthScore)
        .where(HealthScore.project_id == project_id)
        .order_by(HealthScore.calculated_at.desc())
        .limit(1)
    )


def health_history(db: Session, project_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.execute(
            select(HealthScore, Build.build_number)
            .join(Build, Build.id == HealthScore.build_id)
            .where(HealthScore.project_id == project_id)
            .order_by(Build.build_number.asc())
        ).all()
    )
    return [
        {
            "build_number": number,
            "build_id": h.build_id,
            "created_at": h.calculated_at,
            "overall_score": h.overall_score,
            "build_health": h.build_health,
            "code_quality": h.code_quality,
            "testing": h.testing,
            "performance": h.performance,
            "maintainability": h.maintainability,
            "architecture": h.architecture,
            "grade": h.grade,
        }
        for h, number in rows
    ]


def _series_for_project(db: Session, project_id: uuid.UUID) -> dict[str, list[float]]:
    builds = list(
        db.execute(
            select(Build).where(Build.project_id == project_id).order_by(Build.build_number.asc())
        ).scalars()
    )
    series: dict[str, list[float]] = defaultdict(list)
    for b in builds:
        if b.duration_ms is not None:
            series["build_duration_ms"].append(float(b.duration_ms))
        if b.compiler_warnings:
            series["compiler_warnings"].append(float(b.compiler_warnings))
        if b.metrics and b.metrics.binary_size is not None:
            series["binary_size_bytes"].append(float(b.metrics.binary_size))
        series["static_analysis_issues"].append(float(len(b.issues)))
        if b.code_metrics:
            if b.code_metrics.functions_above_threshold is not None:
                series["functions_above_threshold"].append(float(b.code_metrics.functions_above_threshold))
            if b.code_metrics.maintainability_index is not None:
                series["maintainability_index"].append(float(b.code_metrics.maintainability_index))
            if b.code_metrics.avg_function_complexity is not None:
                series["avg_function_complexity"].append(float(b.code_metrics.avg_function_complexity))
        passed = sum(1 for t in b.test_results if t.status == "passed")
        if b.test_results:
            series["test_pass_rate"].append(passed / len(b.test_results))
            series["test_count"].append(float(len(b.test_results)))
        if b.arch_metrics:
            series["architecture_drift_score"].append(float(b.arch_metrics.drift_score))
    return {k: v for k, v in series.items() if v}


def trends(db: Session, project_id: uuid.UUID) -> list[dict]:
    series = _series_for_project(db, project_id)
    out = []
    for metric, values in sorted(series.items()):
        t = classify_trend(metric, values)
        out.append(
            {
                "metric": metric,
                "current": t.current,
                "previous": t.previous,
                "change_percent": t.change_percent,
                "moving_avg": t.moving_avg,
                "direction": t.direction,
                "anomaly": t.anomaly,
                "direction_semantics": "lower_is_better" if DIRECTION_FOR_METRIC.get(metric, True) else "higher_is_better",
            }
        )
    return out


def insights(db: Session, project_id: uuid.UUID, limit: int = 100) -> list[EngineeringInsight]:
    order = {
        "info": 0, "warning": 1, "high": 2, "critical": 3,
    }
    rows = list(
        db.execute(
            select(EngineeringInsight)
            .where(EngineeringInsight.project_id == project_id)
            .order_by(EngineeringInsight.created_at.desc())
            .limit(limit * 8)
        ).scalars()
    )
    rows.sort(key=lambda i: order.get(i.priority, 0), reverse=True)
    return rows[:limit]


def architecture(db: Session, project_id: uuid.UUID) -> dict | None:
    build = latest_build(db, project_id)
    if build is None or build.arch_metrics is None:
        return None
    am: ArchitectureMetrics = build.arch_metrics
    violations = list(
        db.execute(
            select(ArchitectureViolation)
            .where(ArchitectureViolation.build_id == build.id)
            .order_by(ArchitectureViolation.violation_type.asc())
        ).scalars()
    )
    return {
        "build_id": build.id,
        "drift_score": am.drift_score,
        "layer_violations": am.layer_violations,
        "cyclic_dependencies": am.cyclic_dependencies,
        "unexpected_coupling": am.unexpected_coupling,
        "direction_violations": am.direction_violations,
        "module_count": am.module_count,
        "edge_count": am.edge_count,
        "graph": am.dependency_graph or {},
        "violations": [
            {
                "violation_type": v.violation_type,
                "source_module": v.source_module,
                "target_module": v.target_module,
                "source_layer": v.source_layer,
                "target_layer": v.target_layer,
                "message": v.message,
                "approval": v.approval,
            }
            for v in violations
        ],
        "drift_severity": _drift_severity(am.drift_score),
    }


def _drift_severity(score: float) -> str:
    if score < 15:
        return "LOW"
    if score < 40:
        return "MEDIUM"
    return "HIGH"


def benchmarks(db: Session, project_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.execute(
            select(Build.build_number, BenchmarkResult)
            .join(BenchmarkResult, BenchmarkResult.build_id == Build.id)
            .where(Build.project_id == project_id)
            .order_by(Build.build_number.asc(), BenchmarkResult.name.asc())
        ).all()
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for number, b in rows:
        grouped[b.name].append(
            {
                "build_number": number,
                "build_id": b.build_id,
                "mean_ms": b.mean_ms,
                "median_ms": b.median_ms,
                "stddev_ms": b.stddev_ms,
                "cpu_ms": b.cpu_ms,
                "throughput": b.throughput,
            }
        )
    out = []
    for name, points in sorted(grouped.items()):
        current = points[-1]
        previous = points[-2] if len(points) > 1 else None
        change = None
        if previous and current and previous["mean_ms"] and current["mean_ms"] and previous["mean_ms"] > 0:
            change = (current["mean_ms"] - previous["mean_ms"]) / previous["mean_ms"] * 100.0
        status = "OK"
        if change is not None:
            if change > 25:
                status = "CRITICAL"
            elif change > 10:
                status = "WARNING"
            elif change < -5:
                status = "IMPROVING"
        out.append(
            {
                "name": name,
                "current_mean_ms": current["mean_ms"],
                "previous_mean_ms": previous["mean_ms"] if previous else None,
                "change_percent": round(change, 1) if change is not None else None,
                "status": status if current["mean_ms"] is not None else "NO_DATA",
                "points": points,
            }
        )
    return out


def test_summary(db: Session, project_id: uuid.UUID) -> dict:
    build = latest_build(db, project_id)
    if build is None:
        return {
            "total": 0, "passed": 0, "failed": 0, "skipped": 0,
            "pass_rate": 0.0, "execution_time_ms": 0.0, "flaky_tests": [],
            "stability": [], "missing": True,
        }
    rows = list(
        db.execute(
            select(Build.build_number, TestResult)
            .join(TestResult, TestResult.build_id == Build.id)
            .where(Build.project_id == project_id)
            .order_by(Build.build_number.asc(), TestResult.name.asc())
        ).all()
    )
    latest_results = [r for num, r in rows if num == build.build_number]
    passed = sum(1 for r in latest_results if r.status == "passed")
    failed = sum(1 for r in latest_results if r.status == "failed")
    skipped = sum(1 for r in latest_results if r.status == "skipped")
    dur = sum((r.duration_ms or 0.0) for r in latest_results)

    per_test: dict[str, dict] = defaultdict(lambda: {"passes": 0, "failures": 0, "skips": 0, "last": None, "changes": 0, "suite": ""})
    for _number, r in rows:
        key = r.name
        item = per_test[key]
        item["suite"] = r.suite
        if item["last"] is not None and item["last"] != r.status:
            item["changes"] += 1
        item["last"] = r.status
        if r.status == "passed":
            item["passes"] += 1
        elif r.status == "failed":
            item["failures"] += 1
        else:
            item["skips"] += 1

    stability = []
    flaky_tests = []
    for name, item in per_test.items():
        total = item["passes"] + item["failures"] + item["skips"]
        state_changes = item["changes"]
        flaky_score = state_changes / total if total else 0.0
        status = "stable"
        if state_changes >= 2 and total >= 3:
            status = "flaky"
            flaky_tests.append(name)
        elif item["failures"] >= 3:
            status = "frequently_failing"
        elif item["failures"] == 0 and item["passes"] > 0:
            status = "stable"
        elif item["failures"] > 0:
            status = "new_failure" if total <= 2 else "unstable"
        stability.append(
            {
                "name": name, "suite": item["suite"], "executions": total,
                "passes": item["passes"], "failures": item["failures"], "skips": item["skips"],
                "state_changes": state_changes, "flaky_score": round(flaky_score, 3), "status": status,
            }
        )
    stability.sort(key=lambda s: (-s["state_changes"], s["name"]))
    failures = [
        {"name": r.name, "message": r.error_message} for r in latest_results if r.status == "failed"
    ]
    return {
        "total": len(latest_results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(passed / len(latest_results), 4) if latest_results else 0.0,
        "execution_time_ms": dur,
        "flaky_tests": flaky_tests,
        "stability": stability,
        "failures": failures,
        "missing": not latest_results,
    }


def build_history_rows(db: Session, project_id: uuid.UUID, page: int, page_size: int) -> tuple[list[BuildSummary], int]:
    base = select(Build).where(Build.project_id == project_id)
    total = db.scalar(
        select(func.count(Build.id)).where(Build.project_id == project_id)
    ) or 0
    builds = list(
        db.execute(base.order_by(Build.build_number.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    )
    items = []
    for b in builds:
        passed = sum(1 for t in b.test_results if t.status == "passed")
        health = b.health.overall_score if b.health else None
        items.append(
            BuildSummary(
                id=b.id,
                project_id=b.project_id,
                build_number=b.build_number,
                status=b.status,
                duration_ms=b.duration_ms,
                commit_hash=b.commit_hash,
                branch=b.branch,
                compiler_warnings=b.compiler_warnings,
                compiler_errors=b.compiler_errors,
                created_at=b.created_at,
                health_score=health,
                test_summary={"passed": passed, "total": len(b.test_results)},
                issue_count=len(b.issues),
            )
        )
    return items, total
