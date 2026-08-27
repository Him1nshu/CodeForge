"""Project management service (CRUD + API key rotation)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.build import Build
from app.models.health import HealthScore
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectError(Exception):
    pass


def list_projects(db: Session, q: str | None = None) -> list[Project]:
    stmt = select(Project).order_by(Project.created_at.asc())
    if q:
        stmt = stmt.where(Project.project_name.ilike(f"%{q}%"))
    return list(db.execute(stmt).scalars())


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = get_project(db, project_id)
    if project is None:
        raise ProjectError("project not found")
    return project


def create_project(db: Session, data: ProjectCreate) -> Project:
    if db.execute(select(Project).where(Project.project_name == data.project_name)).scalar_one_or_none():
        raise ProjectError("a project with this name already exists")

    project = Project(
        project_name=data.project_name,
        repository_url=data.repository_url,
        branch=data.branch,
        build_command=data.build_command,
        test_command=data.test_command,
        benchmark_command=data.benchmark_command,
        binary_path=data.binary_path,
        analysis_tools=data.analysis_tools.model_dump() if data.analysis_tools else {"enabled": []},
        health_config=data.health_config or {},
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "analysis_tools" and value is not None:
            value = value.model_dump()
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def rotate_api_key(db: Session, project: Project) -> str:
    """Generate and store a new API key digest; return the plaintext once."""
    plain = generate_api_key()
    project.api_key_hash = hash_api_key(plain)
    db.commit()
    return plain


def clear_api_key(db: Session, project: Project) -> None:
    project.api_key_hash = None
    db.commit()


def project_summary(db: Session, project: Project) -> dict:
    build_count = db.scalar(
        select(func.count(Build.id)).where(Build.project_id == project.id)
    ) or 0
    latest_health = db.scalar(
        select(HealthScore.overall_score)
        .where(HealthScore.project_id == project.id)
        .order_by(HealthScore.calculated_at.desc())
        .limit(1)
    )
    return {"build_count": build_count, "latest_health": latest_health}
