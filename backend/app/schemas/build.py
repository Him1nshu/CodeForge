"""Build report (collector contract) and build response schemas.

The BuildReport schema is the single validation contract used both by the
`buildpulse` CLI (writing build_report.json) and the backend ingestion endpoint.
"""

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Collector report schema (input to POST /api/projects/{id}/builds)
# ---------------------------------------------------------------------------


class ReportEnvironment(BaseModel):
    os: str | None = None
    compiler: str | None = None
    compiler_version: str | None = None
    cmake_version: str | None = None
    tool_versions: dict[str, str] = Field(default_factory=dict)


class ReportBuild(BaseModel):
    status: str = "SUCCESS"
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    commit_hash: str | None = None
    branch: str | None = None
    commit_message: str | None = None
    commit_author: str | None = None
    commit_timestamp: datetime | None = None
    changed_files: int | None = None
    lines_added: int | None = None
    lines_removed: int | None = None
    compiler_warnings: int = 0
    compiler_errors: int = 0
    build_retries: int = 0
    collector_run_id: str | None = None
    environment: ReportEnvironment = Field(default_factory=ReportEnvironment)


class ReportMetrics(BaseModel):
    binary_size: int | None = None
    binary_size_change: int | None = None
    pct_binary_growth: float | None = None
    artifact_count: int | None = None
    artifact_paths: list[str] = Field(default_factory=list)


class ReportComplexity(BaseModel):
    lines_of_code: int | None = None
    functions: int | None = None
    cyclomatic_complexity_total: int | None = None
    avg_function_complexity: float | None = None
    max_function_complexity: int | None = None
    functions_above_threshold: int | None = None
    complexity_threshold: int = 15
    maintainability_index: float | None = None
    avg_function_length: float | None = None
    top_complex_functions: list[dict[str, Any]] = Field(default_factory=list)


class ReportIssue(BaseModel):
    tool: str
    file: str
    line: int | None = None
    severity: str = "low"
    rule: str | None = None
    message: str
    category: str = "other"


class ReportTest(BaseModel):
    suite: str = ""
    name: str
    status: str = "passed"
    duration_ms: float | None = None
    error: str | None = None


class ReportBenchmark(BaseModel):
    name: str
    mean_ms: float | None = None
    median_ms: float | None = None
    stddev_ms: float | None = None
    cpu_ms: float | None = None
    throughput: float | None = None
    iterations: int | None = None


class ReportDependency(BaseModel):
    name: str
    version: str | None = None
    type: str = "unknown"
    change: str = "unchanged"
    previous_version: str | None = None


class ReportEdge(BaseModel):
    source: str
    target: str


class ReportArchitecture(BaseModel):
    module_count: int = 0
    edge_count: int = 0
    edges: list[ReportEdge] = Field(default_factory=list)
    layer_mapping: dict[str, str] = Field(default_factory=dict)


class BuildReport(BaseModel):
    """Top-level collector report — the ingestion contract."""

    build: ReportBuild = Field(default_factory=ReportBuild)
    metrics: ReportMetrics = Field(default_factory=ReportMetrics)
    tests: list[ReportTest] = Field(default_factory=list)
    benchmarks: list[ReportBenchmark] = Field(default_factory=list)
    static_analysis: list[ReportIssue] = Field(default_factory=list)
    complexity: ReportComplexity = Field(default_factory=ReportComplexity)
    dependencies: list[ReportDependency] = Field(default_factory=list)
    architecture: ReportArchitecture = Field(default_factory=ReportArchitecture)

    @field_validator("static_analysis")
    @classmethod
    def _cap_issues(cls, v: list[ReportIssue]) -> list[ReportIssue]:
        return v  # size guard enforced at HTTP layer / repository layer


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class BuildSummary(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    build_number: int
    status: str
    duration_ms: int | None
    commit_hash: str | None
    branch: str | None
    compiler_warnings: int
    compiler_errors: int
    created_at: datetime
    health_score: float | None = None
    test_summary: dict[str, int] = Field(default_factory=dict)
    issue_count: int = 0

    model_config = {"from_attributes": True}


class BuildIngestResponse(BaseModel):
    build_id: uuid.UUID
    build_number: int
    health_score: float | None = None
    insights_created: int = 0
    duplicate: bool = False
    note: str = ""

    model_config = {"from_attributes": True}


class BuildDetail(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    build_number: int
    status: str
    start_time: datetime | None
    end_time: datetime | None
    duration_ms: int | None
    commit_hash: str | None
    branch: str | None
    commit_message: str | None
    commit_author: str | None
    commit_timestamp: datetime | None
    changed_files: int | None
    lines_added: int | None
    lines_removed: int | None
    compiler_warnings: int
    compiler_errors: int
    build_retries: int
    environment: dict[str, Any]
    created_at: datetime
    metrics: dict[str, Any] | None = None
    code_metrics: dict[str, Any] | None = None
    arch_metrics: dict[str, Any] | None = None
    health: dict[str, Any] | None = None
    test_summary: dict[str, Any] = Field(default_factory=dict)
    issue_summary: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
