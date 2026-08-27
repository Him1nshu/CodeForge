"""Project request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisTools(BaseModel):
    enabled: list[str] = Field(
        default_factory=lambda: ["clang-tidy", "cppcheck", "lizard", "ctest", "cmake"]
    )
    layer_mapping: dict[str, str] | None = None


class ProjectCreate(BaseModel):
    project_name: str = Field(min_length=1, max_length=200)
    repository_url: str | None = None
    branch: str = "main"
    build_command: str | None = None
    test_command: str | None = None
    benchmark_command: str | None = None
    binary_path: str | None = None
    analysis_tools: AnalysisTools | None = None
    health_config: dict[str, object] = Field(
        default_factory=lambda: {
            "weights": {
                "build": 0.15,
                "code_quality": 0.20,
                "testing": 0.20,
                "performance": 0.15,
                "maintainability": 0.15,
                "architecture": 0.15,
            }
        }
    )


class ProjectUpdate(BaseModel):
    branch: str | None = None
    build_command: str | None = None
    test_command: str | None = None
    benchmark_command: str | None = None
    binary_path: str | None = None
    analysis_tools: AnalysisTools | None = None
    health_config: dict[str, object] | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    project_name: str
    repository_url: str | None
    branch: str
    build_command: str | None
    test_command: str | None
    benchmark_command: str | None
    binary_path: str | None
    analysis_tools: dict
    health_config: dict
    created_at: datetime
    updated_at: datetime
    build_count: int = 0
    latest_health: float | None = None

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    api_key: str
    note: str = "Store this key; only the digest is kept by the server."
