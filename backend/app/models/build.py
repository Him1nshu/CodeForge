"""builds and build_metrics tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JsonType


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Build(Base):
    __tablename__ = "builds"
    __table_args__ = (
        Index("ix_builds_project_number", "project_id", "build_number"),
        Index("ix_builds_project_commit", "project_id", "commit_hash"),
        Index("ix_builds_project_created", "project_id", "created_at"),
        Index("ix_builds_project_collector_run", "project_id", "collector_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    build_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    commit_hash: Mapped[str | None] = mapped_column(String(64))
    branch: Mapped[str | None] = mapped_column(String(200))
    commit_message: Mapped[str | None] = mapped_column(Text)
    commit_author: Mapped[str | None] = mapped_column(String(200))
    commit_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changed_files: Mapped[int | None] = mapped_column(Integer)
    lines_added: Mapped[int | None] = mapped_column(Integer)
    lines_removed: Mapped[int | None] = mapped_column(Integer)
    compiler_warnings: Mapped[int] = mapped_column(Integer, default=0)
    compiler_errors: Mapped[int] = mapped_column(Integer, default=0)
    build_retries: Mapped[int] = mapped_column(Integer, default=0)
    collector_run_id: Mapped[str | None] = mapped_column(String(100))
    environment: Mapped[dict] = mapped_column(JsonType, default=dict)
    raw_report: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    project = relationship("Project", back_populates="builds")
    metrics = relationship("BuildMetrics", back_populates="build", uselist=False, cascade="all, delete-orphan")
    code_metrics = relationship("CodeMetrics", back_populates="build", uselist=False, cascade="all, delete-orphan")
    issues = relationship("StaticAnalysisIssue", back_populates="build", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="build", cascade="all, delete-orphan")
    benchmarks = relationship("BenchmarkResult", back_populates="build", cascade="all, delete-orphan")
    dependencies = relationship("DependencyRecord", back_populates="build", cascade="all, delete-orphan")
    arch_metrics = relationship("ArchitectureMetrics", back_populates="build", uselist=False, cascade="all, delete-orphan")
    arch_violations = relationship("ArchitectureViolation", back_populates="build", cascade="all, delete-orphan")
    health = relationship("HealthScore", back_populates="build", uselist=False, cascade="all, delete-orphan")
    insights = relationship("EngineeringInsight", back_populates="build", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Build #{self.build_number} {self.status}>"


class BuildMetrics(Base):
    __tablename__ = "build_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("builds.id", ondelete="CASCADE"), unique=True
    )
    binary_size: Mapped[int | None] = mapped_column(BigInteger)
    binary_size_change: Mapped[int | None] = mapped_column(BigInteger)
    pct_binary_growth: Mapped[float | None]
    artifact_count: Mapped[int | None] = mapped_column(Integer)
    artifact_paths: Mapped[list] = mapped_column(JsonType, default=list)

    build = relationship("Build", back_populates="metrics")
