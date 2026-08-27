"""End-to-end API integration tests (SQLite-backed TestClient).

Models the spec's 5-version degradation story against the public API.
"""

import pytest
from conftest import sample_report


def _create_project(client, name: str = "SampleCppProject") -> dict:
    resp = client.post("/api/projects", json={
        "project_name": name,
        "repository_url": "https://github.com/example/sample-cpp-project",
        "branch": "main",
        "build_command": "cmake --build build",
        "test_command": "ctest --test-dir build",
        "binary_path": "build/bin/application",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_swagger_is_served(client) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
    openapi = client.get("/openapi.json").json()
    assert "/api/projects" in openapi["paths"]
    assert "/api/projects/{project_id}/builds" in openapi["paths"]


def test_project_lifecycle(client) -> None:
    project = _create_project(client)
    assert project["project_name"] == "SampleCppProject"
    assert project["build_count"] == 0

    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    pid = project["id"]
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200

    resp = client.patch(f"/api/projects/{pid}", json={"branch": "develop"})
    assert resp.status_code == 200
    assert resp.json()["branch"] == "develop"

    resp = client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 204


def test_duplicate_project_rejected(client) -> None:
    _create_project(client, "UniqueName")
    resp = client.post("/api/projects", json={"project_name": "UniqueName"})
    assert resp.status_code == 409


def test_ingest_healthy_build_and_query_endpoints(client) -> None:
    project = _create_project(client)
    pid = project["id"]
    report = sample_report()
    resp = client.post(f"/api/projects/{pid}/builds", json=report)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["duplicate"] is False
    assert body["build_number"] == 1
    assert body["health_score"] is not None and body["health_score"] >= 85

    # Health endpoints
    health = client.get(f"/api/projects/{pid}/health").json()
    assert health["overall_score"] == body["health_score"]
    assert health["grade"] in ("EXCELLENT", "GOOD")

    hist = client.get(f"/api/projects/{pid}/health/history").json()
    assert len(hist) == 1

    metrics = client.get(f"/api/projects/{pid}/metrics").json()
    assert metrics["build"]["duration_ms"] == 90000
    assert metrics["code_metrics"]["maintainability_index"] == 82.0

    trends = client.get(f"/api/projects/{pid}/trends").json()
    assert {t["metric"] for t in trends} == {
        "build_duration_ms", "compiler_warnings", "binary_size_bytes",
        "static_analysis_issues", "functions_above_threshold",
        "maintainability_index", "avg_function_complexity",
        "test_pass_rate", "test_count", "architecture_drift_score",
    }

    insights = client.get(f"/api/projects/{pid}/insights").json()
    assert insights, "healthy build should still emit an info insight"

    arch = client.get(f"/api/projects/{pid}/architecture").json()
    assert arch["drift_score"] == 0.0
    assert arch["graph"]["nodes"]

    benches = client.get(f"/api/projects/{pid}/benchmarks").json()
    assert {b["name"] for b in benches} == {"vector_processing", "hash_lookup"}

    tests = client.get(f"/api/projects/{pid}/tests").json()
    assert tests["passed"] == 3 and tests["failed"] == 0

    hist_rows = client.get(f"/api/projects/{pid}/build-history").json()
    assert hist_rows["total"] == 1

    listing = client.get("/api/builds").json()
    assert listing["total"] == 1

    detail = client.get(f"/api/builds/{body['build_id']}").json()
    assert detail["build_number"] == 1
    assert detail["test_summary"]["passed"] == 3
    assert detail["issue_summary"] == {}


def test_duplicate_ingest_not_double_counted(client) -> None:
    project = _create_project(client)
    pid = project["id"]
    first = client.post(f"/api/projects/{pid}/builds", json=sample_report())
    assert first.status_code == 201
    # Same commit + same collector_run_id -> duplicate marker, no new build.
    dup = client.post(f"/api/projects/{pid}/builds", json=sample_report())
    assert dup.status_code == 201
    assert dup.json()["duplicate"] is True
    assert client.get(f"/api/projects/{pid}/build-history").json()["total"] == 1


def test_degradation_across_five_versions(client) -> None:
    """Spec §14/§20 story: v1..v5 degrade; health must decline monotonically-ish
    and the API must surface it (issues, regressions, drift, failures)."""
    project = _create_project(client)
    pid = project["id"]

    def report_for(version: int, commit: str) -> dict:
        duration = [90000, 95000, 121000, 126000, 135000][version - 1]
        warnings = [10, 12, 16, 22, 28][version - 1]
        issues = build_issues(version)
        complexity = {
            1: {"avg_function_complexity": 4.7, "max_function_complexity": 12,
                "functions_above_threshold": 1, "maintainability_index": 82.0},
            2: {"avg_function_complexity": 5.6, "max_function_complexity": 17,
                "functions_above_threshold": 3, "maintainability_index": 76.0},
            3: {"avg_function_complexity": 6.1, "max_function_complexity": 19,
                "functions_above_threshold": 4, "maintainability_index": 72.0},
            4: {"avg_function_complexity": 6.6, "max_function_complexity": 23,
                "functions_above_threshold": 6, "maintainability_index": 67.0},
            5: {"avg_function_complexity": 7.4, "max_function_complexity": 26,
                "functions_above_threshold": 9, "maintainability_index": 61.0},
        }[version]
        benchmark_mean = [120.0, 118.0, 114.0, 168.0, 175.0][version - 1]
        failed_tests = 0 if version < 4 else (2 if version == 4 else 4)
        passed_tests = 20 - failed_tests
        failed_names = ["test_0", "test_1"] if version == 4 else ["test_0", "test_2", "test_3", "test_4"]
        edges = [
            {"source": "presentation", "target": "application"},
            {"source": "application", "target": "domain"},
            {"source": "domain", "target": "infrastructure"},
        ]
        if version == 5:
            edges.append({"source": "domain", "target": "presentation"})
        return sample_report(
            build={
                **sample_report()["build"],
                "status": "SUCCESS" if version < 4 else "FAILURE",
                "duration_ms": duration,
                "commit_hash": commit,
                "commit_message": f"version {version}",
                "collector_run_id": f"run-v{version}",
                "compiler_warnings": warnings,
            },
            static_analysis=issues,
            complexity={**sample_report()["complexity"], "lines_of_code": 3000 + version * 300, **complexity},
            benchmarks=[{"name": "vector_processing", "mean_ms": benchmark_mean, "median_ms": benchmark_mean - 2,
                         "stddev_ms": 3.0, "cpu_ms": benchmark_mean - 5, "throughput": 1000.0, "iterations": 10}],
            tests=[
                {"suite": "unit", "name": f"test_{i}",
                 "status": "failed" if f"test_{i}" in failed_names else "passed",
                 "duration_ms": 1.0,
                 "error": f"expectation failed in test_{i}" if f"test_{i}" in failed_names else None}
                for i in range(passed_tests + failed_tests)
            ],
            architecture={**sample_report()["architecture"], "edges": edges},
        )

    def build_issues(version: int) -> list[dict]:
        count = [0, 5, 12, 21, 34][version - 1]

        def severity_for(i: int) -> str:
            if i % 4 == 0:
                return "critical"
            if i % 4 == 1:
                return "high"
            if i % 4 == 2:
                return "medium"
            return "low"

        return [
            {"tool": "clang-tidy", "file": "src/parser.cpp", "line": 10 + i,
             "severity": severity_for(i), "rule": f"rule-{i}",
             "message": "accumulating warning", "category": "code-smell"}
            for i in range(count)
        ]

    scores = []
    for v in range(1, 6):
        report = report_for(v, f"c0mm1t{v}")
        resp = client.post(f"/api/projects/{pid}/builds", json=report)
        assert resp.status_code == 201, resp.text
        scores.append(resp.json()["health_score"])

    # v1 healthiest; story must visibly degrade.
    assert scores[0] > scores[4]
    assert scores[4] < 65
    assert scores[4] < scores[0] - 20

    # Health history length 5 and each build recorded once.
    hist = client.get(f"/api/projects/{pid}/health/history").json()
    assert len(hist) == 5
    assert [p["overall_score"] for p in hist] == pytest.approx(scores, abs=0.02)

    # Version 5 should trigger architecture drift + test failures + perf insight.
    arch = client.get(f"/api/projects/{pid}/architecture").json()
    assert arch["drift_score"] > 0
    assert arch["layer_violations"] >= 1

    tests = client.get(f"/api/projects/{pid}/tests").json()
    assert tests["failed"] == 4
    assert tests["pass_rate"] < 1.0
    # failure messages survive the full journey and are queryable
    assert len(tests["failures"]) == 4
    assert all(f["message"] and "test_" in str(f["message"]) for f in tests["failures"])

    latest_insights = client.get(f"/api/projects/{pid}/insights", params={"limit": 100}).json()
    priorities = {i["priority"] for i in latest_insights}
    assert "critical" in priorities or "high" in priorities

    # Benchmark series must contain a >30% jump between adjacent builds.
    benches = client.get(f"/api/projects/{pid}/benchmarks").json()
    vb = next(b for b in benches if b["name"] == "vector_processing")
    assert vb["current_mean_ms"] == 175.0
    assert vb["status"] in ("OK", "WARNING", "CRITICAL")
    means = [p["mean_ms"] for p in vb["points"]]
    jumps = [(means[i + 1] - means[i]) / means[i] * 100 for i in range(len(means) - 1)]
    assert max(jumps) > 30
