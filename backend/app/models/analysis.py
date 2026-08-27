"""Per-build analysis aggregates: code metrics, static issues, tests,
benchmarks, dependencies and architecture records (doc 04)."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JsonType


class CodeMetrics(Base):
    __tablename__ = "code_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("builds.id", ondelete="CASCADE"), unique=True
    )
    lines_of_code: Mapped[int | None] = mapped_column(Integer)
    functions: Mapped[int | None] = mapped_column(Integer)
    cyclomatic_complexity_total: Mapped[int | None] = mapped_column(Integer)
    avg_function_complexity: Mapped[float | None]
    max_function_complexity: Mapped[int | None] = mapped_column(Integer)
    functions_above_threshold: Mapped[int | None] = mapped_column(Integer)
    complexity_threshold: Mapped[int] = mapped_column(Integer, default=15)
    maintainability_index: Mapped[float | None]
    avg_function_length: Mapped[float | None]
    top_complex_functions: Mapped[list] = mapped_column(JsonType, default=list)

    build = relationship("Build", back_populates="code_metrics")


class StaticAnalysisIssue(Base):
    __tablename__ = "static_analysis_issues"
    __table_args__ = (
        UniqueConstraint(
            "build_id", "tool", "file", "line", "rule", name="uq_issue_dedupe"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    file: Mapped[str] = mapped_column(Text)
    line: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), default="low")
    rule: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="other")

    build = relationship("Build", back_populates="issues")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint("build_id", "suite", "name", name="uq_test_dedupe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    suite: Mapped[str] = mapped_column(String(200), default="")
    name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="passed")
    duration_ms: Mapped[float | None]
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    build = relationship("Build", back_populates="test_results")


class BenchmarkResult(Base):
    __tablename__ = "benchmarks"
    __table_args__ = (UniqueConstraint("build_id", "name", name="uq_benchmark_dedupe"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    mean_ms: Mapped[float | None]
    median_ms: Mapped[float | None]
    stddev_ms: Mapped[float | None]
    cpu_ms: Mapped[float | None]
    throughput: Mapped[float | None]
    iterations: Mapped[int | None] = mapped_column(Integer)

    build = relationship("Build", back_populates="benchmarks")


class DependencyRecord(Base):
    __tablename__ = "dependencies"
    __table_args__ = (UniqueConstraint("build_id", "name", name="uq_dependency_dedupe"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50), default="unknown")
    change: Mapped[str] = mapped_column(String(20), default="unchanged")
    previous_version: Mapped[str | None] = mapped_column(String(100))

    build = relationship("Build", back_populates="dependencies")


class ArchitectureMetrics(Base):
    __tablename__ = "architecture_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("builds.id", ondelete="CASCADE"), unique=True
    )
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)
    layer_violations: Mapped[int] = mapped_column(Integer, default=0)
    cyclic_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    unexpected_coupling: Mapped[int] = mapped_column(Integer, default=0)
    direction_violations: Mapped[int] = mapped_column(Integer, default=0)
    module_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    dependency_graph: Mapped[dict] = mapped_column(JsonType, default=dict)

    build = relationship("Build", back_populates="arch_metrics")


class ArchitectureViolation(Base):
    __tablename__ = "architecture_violations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    build_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    violation_type: Mapped[str] = mapped_column(String(40))
    source_module: Mapped[str] = mapped_column(String(200))
    target_module: Mapped[str] = mapped_column(String(200))
    source_layer: Mapped[str | None] = mapped_column(String(100))
    target_layer: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    approval: Mapped[str] = mapped_column(String(20), default="open")

    build = relationship("Build", back_populates="arch_violations")
