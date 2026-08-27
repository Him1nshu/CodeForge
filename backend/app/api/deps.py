"""Shared FastAPI dependencies."""

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import verify_api_key
from app.models.project import Project


def get_project_or_404(db: Session = Depends(get_db), project_id: uuid.UUID | None = None) -> Project:
    if project_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_id required")
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


def optional_project_auth(
    project: Project = Depends(get_project_or_404),
    x_api_key: str | None = Header(default=None),
) -> Project:
    """Enforce a per-project API key only when the project has one configured."""
    if project.api_key_hash and (not x_api_key or not verify_api_key(x_api_key, project.api_key_hash)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid X-API-Key")
    return project
