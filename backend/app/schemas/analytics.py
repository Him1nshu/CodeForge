"""Schemas for analytics endpoints (health, trends, insights, architecture,
benchmarks, tests)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CategoryScores(BaseModel):
    build: float
    code_quality: float
    testing: float
    performance: float
    maintainability: float
    architecture: float


class HealthScoreResponse(BaseModel):
    build_id: uuid.UUID
    build_number: int
    overall_score: float
    grade: str
    categories: CategoryScores
    weights: dict[str, float]
    formula_version: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    calculated_at: datetime


class HealthHistoryPoint(BaseModel):
    build_number: int
    build_id: uuid.UUID
    created_at: datetime
    overall_score: float
    build_health: float
    code_quality: float
    testing: float
    performance: float
    maintainability: float
    architecture: float
    grade: str


class TrendItem(BaseModel):
    metric: str
    current: float | None
    previous: float | None
    change_percent: float | None
    moving_avg: float | None
    direction: str
    anomaly: bool = False


class MetricBundle(BaseModel):
    build: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    code_metrics: dict[str, Any] = Field(default_factory=dict)
    tests: dict[str, Any] = Field(default_factory=dict)
    benchmarks: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: dict[str, Any] = Field(default_factory=dict)
    architecture: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)


class InsightResponse(BaseModel):
    id: uuid.UUID
    build_id: uuid.UUID
    build_number: int | None = None
    priority: str
    category: str
    title: str
    message: str
    recommendation: str
    evidence: dict[str, Any]
    created_at: datetime


class ArchitectureResponse(BaseModel):
    build_id: uuid.UUID
    drift_score: float
    layer_violations: int
    cyclic_dependencies: int
    unexpected_coupling: int
    direction_violations: int
    module_count: int
    edge_count: int
    graph: dict[str, Any]
    violations: list[dict[str, Any]] = Field(default_factory=list)


class BenchmarkPoint(BaseModel):
    build_number: int
    build_id: uuid.UUID
    mean_ms: float | None
    median_ms: float | None
    stddev_ms: float | None
    cpu_ms: float | None
    throughput: float | None


class BenchmarkSeries(BaseModel):
    name: str
    current_mean_ms: float | None
    previous_mean_ms: float | None
    change_percent: float | None
    status: str
    points: list[BenchmarkPoint] = Field(default_factory=list)


class TestStabilityRow(BaseModel):
    name: str
    suite: str
    executions: int
    passes: int
    failures: int
    skips: int
    state_changes: int
    flaky_score: float
    status: str


class TestFailureRow(BaseModel):
    name: str
    message: str | None = None


class TestSummaryResponse(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    execution_time_ms: float
    flaky_tests: list[str] = Field(default_factory=list)
    stability: list[TestStabilityRow] = Field(default_factory=list)
    failures: list[TestFailureRow] = Field(default_factory=list)


class BuildHistoryRow(BaseModel):
    build_id: uuid.UUID
    build_number: int
    commit: str | None
    branch: str | None
    status: str
    duration_ms: int | None
    health_score: float | None
    tests_passed: int
    tests_total: int
    warnings: int
    issues: int
    created_at: datetime
