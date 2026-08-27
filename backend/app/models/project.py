"""projects table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JsonType


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    repository_url: Mapped[str | None] = mapped_column(String(500))
    branch: Mapped[str] = mapped_column(String(200), default="main")
    build_command: Mapped[str | None] = mapped_column(String(500))
    test_command: Mapped[str | None] = mapped_column(String(500))
    benchmark_command: Mapped[str | None] = mapped_column(String(500))
    binary_path: Mapped[str | None] = mapped_column(String(500))
    analysis_tools: Mapped[dict] = mapped_column(JsonType, default=dict)
    health_config: Mapped[dict] = mapped_column(JsonType, default=dict)
    api_key_hash: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    builds = relationship("Build", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.project_name}>"
