"""Shared test fixtures: SQLite in-memory DB, TestClient, sample report builder."""

import os
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("CODEFORGE_DATABASE_URL", "sqlite:///:memory:")

import app.models
from app.core.db import Base
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    from app.core import db as app_db

    app_db.engine = engine
    app_db.SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestClient(app) as c:
        yield c
    engine.dispose()


def utcnow() -> datetime:
    return datetime.now(UTC)


def sample_report(**overrides) -> dict:
    """A healthy v1-style report; tests override fields to model degradation."""
    report = {
        "build": {
            "status": "SUCCESS",
            "start_time": utcnow().isoformat(),
            "end_time": utcnow().isoformat(),
            "duration_ms": 90000,
            "commit_hash": "abcdef1234567890",
            "branch": "main",
            "commit_message": "healthy baseline",
            "commit_author": "dev",
            "commit_timestamp": utcnow().isoformat(),
            "changed_files": 3,
            "lines_added": 40,
            "lines_removed": 5,
            "compiler_warnings": 10,
            "compiler_errors": 0,
            "build_retries": 0,
            "collector_run_id": "run-0001",
            "environment": {"os": "linux", "compiler": "g++ 13", "tool_versions": {}},
        },
        "metrics": {"binary_size": 1024000, "binary_size_change": 0, "pct_binary_growth": 0.0,
                    "artifact_count": 1, "artifact_paths": ["build/bin/app"]},
        "tests": [
            {"suite": "unit", "name": "test_parser", "status": "passed", "duration_ms": 1.0},
            {"suite": "unit", "name": "test_network", "status": "passed", "duration_ms": 2.0},
            {"suite": "unit", "name": "test_storage", "status": "passed", "duration_ms": 1.5},
        ],
        "benchmarks": [
            {"name": "vector_processing", "mean_ms": 120.0, "median_ms": 118.0, "stddev_ms": 3.0,
             "cpu_ms": 115.0, "throughput": 1000.0, "iterations": 10},
            {"name": "hash_lookup", "mean_ms": 45.0, "median_ms": 44.0, "stddev_ms": 1.0,
             "cpu_ms": 43.0, "throughput": 500.0, "iterations": 10},
        ],
        "static_analysis": [],
        "complexity": {"lines_of_code": 3000, "functions": 90, "cyclomatic_complexity_total": 420,
                       "avg_function_complexity": 4.7, "max_function_complexity": 12,
                       "functions_above_threshold": 1, "complexity_threshold": 15,
                       "maintainability_index": 82.0, "avg_function_length": 30.0,
                       "top_complex_functions": [{"file": "src/io.cpp", "function": "decode", "complexity": 12}]},
        "dependencies": [
            {"name": "spdlog", "version": "1.13", "type": "conan", "change": "unchanged", "previous_version": None},
            {"name": "fmt", "version": "9.1", "type": "conan", "change": "unchanged", "previous_version": None},
        ],
        "architecture": {"module_count": 3, "edge_count": 2,
                         "edges": [{"source": "presentation", "target": "application"},
                                   {"source": "application", "target": "domain"}],
                         "layer_mapping": {
                             "presentation": "presentation",
                             "application": "application",
                             "domain": "domain",
                             "infrastructure": "infrastructure",
                         }},
    }
    report.update(overrides)
    return report
