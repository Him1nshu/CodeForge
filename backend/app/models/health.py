"""health_scores and engineering_insights tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JsonType


def _utcnow() -> datetime:
    return datetime.now(UTC)


class HealthScore(Base):
    __tablename__ = "health_scores"
    __table_args__ = (
        UniqueConstraint("build_id", name="uq_health_score_build"),
        UniqueConstraint("project_id", "build_id", name="uq_health_project_build"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    overall_score: Mapped[float]
    build_health: Mapped[float]
    code_quality: Mapped[float]
    testing: Mapped[float]
    performance: Mapped[float]
    maintainability: Mapped[float]
    architecture: Mapped[float]
    grade: Mapped[str] = mapped_column(String(20))
    formula_version: Mapped[str] = mapped_column(String(10), default="1.0")
    weights: Mapped[dict] = mapped_column(JsonType, default=dict)
    evidence: Mapped[dict] = mapped_column(JsonType, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    build = relationship("Build", back_populates="health")
    project = relationship("Project")


class EngineeringInsight(Base):
    __tablename__ = "engineering_insights"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="info")
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    build = relationship("Build", back_populates="insights")
    project = relationship("Project")
