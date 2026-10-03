# CODEFORGE — API Contracts

Base URL `/api`. Swagger at `/docs`. All list endpoints support
`page`/`page_size` (default 1/50) pagination and return
`{items, total, page, page_size}`. Errors use RFC 7807-ish
`{"detail": "..."}` with proper HTTP codes (400 validation, 404 missing, 409
duplicate, 401/403 auth).

Optional auth: when a project has `api_key_hash`, requests carry
`X-API-Key: <project key>`.

## Projects

| Method | Path | Body / Notes |
| --- | --- | --- |
| POST | `/api/projects` | `ProjectCreate` (see example below) → `201 ProjectResponse` |
| GET | `/api/projects` | list, `?q=` name filter |
| GET | `/api/projects/{id}` | detail incl. latest health summary |
| PATCH | `/api/projects/{id}` | partial update of commands/tools/health_config |
| DELETE | `/api/projects/{id}` | optional cascade delete |

`ProjectCreate`:

```json
{
  "project_name": "SampleCppProject",
  "repository_url": "https://github.com/example/sample-cpp-project",
  "branch": "main",
  "build_command": "cmake --build build",
  "test_command": "ctest --test-dir build",
  "benchmark_command": "ctest --test-dir build -R benchmark",
  "binary_path": "build/bin/application",
  "analysis_tools": {"enabled": ["clang-tidy", "cppcheck", "lizard", "ctest", "cmake"]}
}
```

## Builds & ingestion

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/projects/{id}/builds` | accepts the full collector `build_report.json`; dedupes on `commit_hash + collector_run_id` (`409` if duplicate); recomputes health/trends/insights; `201 BuildIngestResponse` with `{build_id, build_number, health_score, insights: n}` |
| GET | `/api/builds` | list, filters: `project_id`, `status`, `from`, `to`, `q` |
| GET | `/api/builds/{id}` | full detail incl. metrics, issues (paginated), tests (paginated), benchmark summary |

## Analytics (all scoped `project_id`)

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/api/projects/{id}/health` | latest `HealthScoreResponse` |
| GET | `/api/projects/{id}/health/history` | all health rows (chart) |
| GET | `/api/projects/{id}/metrics` | latest raw metrics aggregate (build, code, test, benchmark, drift) |
| GET | `/api/projects/{id}/trends` | per-metric `{metric, current, previous, change_percent, moving_avg, direction, anomaly}` |
| GET | `/api/projects/{id}/insights` | latest insights by priority |
| GET | `/api/projects/{id}/architecture` | drift score, graph, violations |
| GET | `/api/projects/{id}/benchmarks` | benchmark time-series + regressions |
| GET | `/api/projects/{id}/tests` | pass rate, flaky list, stability table |
| GET | `/api/projects/{id}/build-history` | searchable table rows (build id, commit, branch, status, duration, health, tests, warnings, issues, timestamp) |

## Health Score response

```json
{
  "build_id": "…", "build_number": 11,
  "overall_score": 68.2, "grade": "MODERATE",
  "categories": {
    "build": 81.0, "code_quality": 64.5, "testing": 90.0,
    "performance": 55.0, "maintainability": 61.5, "architecture": 58.0
  },
  "weights": {"build": 0.15, "code_quality": 0.20, "testing": 0.20,
              "performance": 0.15, "maintainability": 0.15, "architecture": 0.15},
  "formula_version": "1.0",
  "calculated_at": "…"
}
```

## Insights response

```json
{
  "priority": "HIGH", "category": "performance",
  "title": "Benchmark regression detected",
  "message": "vector_processing 120ms → 165ms (+37.5%)",
  "recommendation": "Investigate recent SIMD/alloc changes; compare with build 10.",
  "evidence": {"metric": "benchmark.mean_ms", "previous": 120.0, "current": 165.0}
}
```

## Design rules

- Controllers never compute; they call `services/ build_repository, scoring,
  trends, insights, architecture`.
- Pydantic schemas mirror DB models 1:1 for reads; ingestion uses one
  `BuildReport` aggregation schema validated on `POST /builds`.
- Every chart the dashboard renders maps to exactly one of these endpoints —
  no hardcoded dashboard values (demo seed data only via `--seed` script).