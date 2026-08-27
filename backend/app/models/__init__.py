"""Model registry — import all models so Alembic autogenerate sees them."""

from app.models.analysis import (
    ArchitectureMetrics,
    ArchitectureViolation,
    BenchmarkResult,
    CodeMetrics,
    DependencyRecord,
    StaticAnalysisIssue,
    TestResult,
)
from app.models.build import Build, BuildMetrics
from app.models.health import EngineeringInsight, HealthScore
from app.models.project import Project

__all__ = [
    "ArchitectureMetrics",
    "ArchitectureViolation",
    "BenchmarkResult",
    "Build",
    "BuildMetrics",
    "CodeMetrics",
    "DependencyRecord",
    "EngineeringInsight",
    "HealthScore",
    "Project",
    "StaticAnalysisIssue",
    "TestResult",
]
