"""Build ingestion and build query endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, optional_project_auth
from app.models.project import Project
from app.schemas.build import (
    BuildDetail,
    BuildIngestResponse,
    BuildReport,
    Paginated,
)
from app.services import build_service

router = APIRouter(prefix="/api", tags=["builds"])


def uuid_or_404(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found") from exc


@router.post("/projects/{project_id}/builds", response_model=BuildIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_build_report(
    project_id: str,
    report: BuildReport,
    db: Annotated[Session, Depends(get_db)],
    project: Annotated[Project, Depends(optional_project_auth)],
) -> BuildIngestResponse:
    """Ingest a full collector build_report.json and run the derived pipeline."""
    try:
        return build_service.ingest_build(db, project, report)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/builds", response_model=Paginated[BuildDetail])
def list_builds(
    db: Annotated[Session, Depends(get_db)],
    project_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> Paginated[BuildDetail]:
    from sqlalchemy import func, select

    from app.models.build import Build as BuildModel

    conditions = []
    if project_id:
        conditions.append(BuildModel.project_id == uuid_or_404(project_id))
    if status_filter:
        conditions.append(BuildModel.status == status_filter.upper())
    total = db.scalar(select(func.count()).select_from(BuildModel).where(*conditions)) or 0
    stmt = select(BuildModel).where(*conditions)
    builds = list(db.execute(stmt.order_by(BuildModel.build_number.desc()).offset((page - 1) * page_size).limit(page_size)).scalars())
    items = [_build_detail(b) for b in builds]
    return Paginated[BuildDetail](items=items, total=total, page=page, page_size=page_size)


@router.get("/builds/{build_id}", response_model=BuildDetail)
def get_build(build_id: str, db: Annotated[Session, Depends(get_db)]) -> BuildDetail:
    from app.models.build import Build as BuildModel

    build = db.get(BuildModel, uuid_or_404(build_id))
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="build not found")
    return _build_detail(build)


def _build_detail(build) -> BuildDetail:
    """Assemble a BuildDetail from a persisted Build row (avoids over-fetching)."""
    metrics = build.metrics
    cm = build.code_metrics
    am = build.arch_metrics
    passed = sum(1 for t in build.test_results if t.status == "passed")
    severity_counts: dict[str, int] = {}
    for issue in build.issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

    return BuildDetail(
        id=build.id,
        project_id=build.project_id,
        build_number=build.build_number,
        status=build.status,
        start_time=build.start_time,
        end_time=build.end_time,
        duration_ms=build.duration_ms,
        commit_hash=build.commit_hash,
        branch=build.branch,
        commit_message=build.commit_message,
        commit_author=build.commit_author,
        commit_timestamp=build.commit_timestamp,
        changed_files=build.changed_files,
        lines_added=build.lines_added,
        lines_removed=build.lines_removed,
        compiler_warnings=build.compiler_warnings,
        compiler_errors=build.compiler_errors,
        build_retries=build.build_retries,
        environment=build.environment or {},
        created_at=build.created_at,
        metrics=_row_dict(metrics),
        code_metrics=_row_dict(cm),
        arch_metrics=_row_dict(am),
        health=_row_dict(build.health),
        test_summary={"passed": passed, "total": len(build.test_results),
                      "failed": len(build.test_results) - passed},
        issue_summary=severity_counts,
    )


def _row_dict(obj):
    if obj is None:
        return None
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    for key in ("build_id", "id", "project_id"):
        d.pop(key, None)
    d.pop("build", None)
    return d
