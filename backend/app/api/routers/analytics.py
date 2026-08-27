"""Dashboard analytics endpoints — one endpoint per chart/panel."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.analytics import (
    ArchitectureResponse,
    BenchmarkSeries,
    BuildHistoryRow,
    HealthHistoryPoint,
    HealthScoreResponse,
    InsightResponse,
    MetricBundle,
    TestSummaryResponse,
    TrendItem,
)
from app.schemas.build import Paginated
from app.services import analytics_service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["analytics"])


def _project_or_404(project_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc


def _health_response(health, build_number: int) -> HealthScoreResponse:
    return HealthScoreResponse(
        build_id=health.build_id,
        build_number=build_number,
        overall_score=health.overall_score,
        grade=health.grade,
        categories={
            "build": health.build_health,
            "code_quality": health.code_quality,
            "testing": health.testing,
            "performance": health.performance,
            "maintainability": health.maintainability,
            "architecture": health.architecture,
        },
        weights=health.weights,
        formula_version=health.formula_version,
        evidence=health.evidence,
        calculated_at=health.calculated_at,
    )


@router.get("/health", response_model=HealthScoreResponse)
def get_health(project_id: str, db: Annotated[Session, Depends(get_db)]) -> HealthScoreResponse:
    pid = _project_or_404(project_id)
    build = analytics_service.latest_build(db, pid)
    health = analytics_service.latest_health(db, pid)
    if build is None or health is None:
        raise HTTPException(status_code=404, detail="no builds yet for this project")
    return _health_response(health, build.build_number)


@router.get("/health/history", response_model=list[HealthHistoryPoint])
def health_history(project_id: str, db: Annotated[Session, Depends(get_db)]) -> list[HealthHistoryPoint]:
    pid = _project_or_404(project_id)
    return [HealthHistoryPoint(**p) for p in analytics_service.health_history(db, pid)]


@router.get("/metrics", response_model=MetricBundle)
def metrics(project_id: str, db: Annotated[Session, Depends(get_db)]) -> MetricBundle:
    pid = _project_or_404(project_id)
    build = analytics_service.latest_build(db, pid)
    if build is None:
        raise HTTPException(status_code=404, detail="no builds yet for this project")
    return MetricBundle(
        build={
            "build_number": build.build_number,
            "status": build.status,
            "duration_ms": build.duration_ms,
            "compiler_warnings": build.compiler_warnings,
            "compiler_errors": build.compiler_errors,
            "commit_hash": build.commit_hash,
            "branch": build.branch,
            "created_at": build.created_at.isoformat(),
        },
        metrics={
            "binary_size": build.metrics.binary_size if build.metrics else None,
            "artifact_count": build.metrics.artifact_count if build.metrics else None,
        },
        code_metrics=_rm(build.code_metrics),
        tests=analytics_service.test_summary(db, pid),
        benchmarks=analytics_service.benchmarks(db, pid),
        dependencies={"count": len(build.dependencies)},
        architecture=_rm(build.arch_metrics),
        health=_rm(build.health),
    )


@router.get("/trends", response_model=list[TrendItem])
def trends(project_id: str, db: Annotated[Session, Depends(get_db)]) -> list[TrendItem]:
    pid = _project_or_404(project_id)
    return [TrendItem(**t) for t in analytics_service.trends(db, pid)]


@router.get("/insights", response_model=list[InsightResponse])
def insights(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=500),
) -> list[InsightResponse]:
    pid = _project_or_404(project_id)
    rows = analytics_service.insights(db, pid, limit=limit)
    out = []
    for row in rows:
        out.append(
            InsightResponse(
                id=row.id,
                build_id=row.build_id,
                priority=row.priority,
                category=row.category,
                title=row.title,
                message=row.message,
                recommendation=row.recommendation,
                evidence=row.evidence,
                created_at=row.created_at,
            )
        )
    return out


@router.get("/architecture", response_model=ArchitectureResponse)
def architecture(project_id: str, db: Annotated[Session, Depends(get_db)]) -> ArchitectureResponse:
    pid = _project_or_404(project_id)
    data = analytics_service.architecture(db, pid)
    if data is None:
        raise HTTPException(status_code=404, detail="no architecture analysis for this project yet")
    return ArchitectureResponse(**data)


@router.get("/benchmarks", response_model=list[BenchmarkSeries])
def benchmarks(project_id: str, db: Annotated[Session, Depends(get_db)]) -> list[BenchmarkSeries]:
    pid = _project_or_404(project_id)
    return [BenchmarkSeries(**b) for b in analytics_service.benchmarks(db, pid)]


@router.get("/tests", response_model=TestSummaryResponse)
def tests(project_id: str, db: Annotated[Session, Depends(get_db)]) -> TestSummaryResponse:
    pid = _project_or_404(project_id)
    return TestSummaryResponse(**analytics_service.test_summary(db, pid))


@router.get("/build-history", response_model=Paginated[BuildHistoryRow])
def build_history(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> Paginated[BuildHistoryRow]:
    pid = _project_or_404(project_id)
    items, total = analytics_service.build_history_rows(db, pid, page, page_size)
    rows = []
    for it in items:
        rows.append(
            BuildHistoryRow(
                build_id=it.id,
                build_number=it.build_number,
                commit=it.commit_hash,
                branch=it.branch,
                status=it.status,
                duration_ms=it.duration_ms,
                health_score=it.health_score,
                tests_passed=it.test_summary.get("passed", 0),
                tests_total=it.test_summary.get("total", 0),
                warnings=it.compiler_warnings,
                issues=it.issue_count,
                created_at=it.created_at,
            )
        )
    return Paginated[BuildHistoryRow](items=rows, total=total, page=page, page_size=page_size)


def _rm(obj):
    if obj is None:
        return None
    return {k: v for k, v in obj.__dict__.items() if not k.startswith("_") and k not in ("build",)}
