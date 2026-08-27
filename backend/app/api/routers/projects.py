"""Project management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.project import Project
from app.schemas.project import (
    ApiKeyResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project: Project, db: Session) -> ProjectResponse:
    summary = project_service.project_summary(db, project)
    return ProjectResponse.model_validate({**project.__dict__, **summary})


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
def create_project(data: ProjectCreate, db: Annotated[Session, Depends(get_db)]) -> ProjectResponse:
    try:
        project = project_service.create_project(db, data)
    except project_service.ProjectError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(project, db)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None),
) -> list[ProjectResponse]:
    return [_to_response(p, db) for p in project_service.list_projects(db, q)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Annotated[Session, Depends(get_db)]) -> ProjectResponse:
    try:
        project_uuid = uuid.UUID(project_id)
        project = project_service.get_project_or_404(db, project_uuid)
    except (ValueError, project_service.ProjectError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found") from exc
    return _to_response(project, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectUpdate, db: Annotated[Session, Depends(get_db)]) -> ProjectResponse:
    try:
        project = project_service.get_project_or_404(db, uuid.UUID(project_id))
    except (ValueError, project_service.ProjectError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found") from exc
    project = project_service.update_project(db, project, data)
    return _to_response(project, db)


@router.post("/{project_id}/api-key", response_model=ApiKeyResponse)
def generate_api_key(project_id: str, db: Annotated[Session, Depends(get_db)]) -> ApiKeyResponse:
    try:
        project = project_service.get_project_or_404(db, uuid.UUID(project_id))
    except (ValueError, project_service.ProjectError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found") from exc
    plain = project_service.rotate_api_key(db, project)
    return ApiKeyResponse(api_key=plain)


@router.delete("/{project_id}/api-key", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(project_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    try:
        project = project_service.get_project_or_404(db, uuid.UUID(project_id))
        project_service.clear_api_key(db, project)
    except (ValueError, project_service.ProjectError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found") from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    try:
        project = project_service.get_project_or_404(db, uuid.UUID(project_id))
    except (ValueError, project_service.ProjectError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found") from exc
    db.delete(project)
    db.commit()
