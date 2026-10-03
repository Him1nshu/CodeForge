# CODEFORGE — Architecture Analysis

## 1. Goal

CODEFORGE is an Engineering Intelligence Platform that extends CI from
"did it pass?" to "is the software getting healthier or sicker over time?". It
collects build, code, test, benchmark, dependency, and architecture metrics
from successive versions of a C++ project, stores them historically, computes
an **Engineering Health Score**, detects trends and anomalies, and serves
actionable insights through a React dashboard.

## 2. Components in scope (from the specification)

| Component | Responsibility |
| --- | --- |
| CODEFORGE Collector | CLI that runs the build/test/benchmark/analysis tools against a C++ checkout and produces `build_report.json` |
| Build Analyzer | Build status, duration, warnings, errors, retries, binary size, artifacts |
| Code Analyzer | Static analysis (clang-tidy, cppcheck), complexity (lizard), dependency/CMake scan |
| Test Analyzer | ctest/Google Test results, coverage (gcov/lcov), flaky-test detection |
| Metrics Processing | Trend analysis, Health Score Engine, anomaly detection, architecture drift |
| PostgreSQL | Historical storage of all raw and derived metrics |
| FastAPI Backend | REST API, validation, pagination, Swagger docs |
| React Dashboard | Overview, Build, Code Quality, Tests, Performance, Architecture, Build History pages |
| CI Integration | GitHub Actions workflow that runs the collector and uploads the report |

## 3. End-to-end data flow

```text
Git repo (C++ project)
   -> GitHub Actions / local
   -> codeforge collect [--project-id P --build-command ... --binary-path ...]
        • builds the project, times it, captures compiler warnings/errors
        • runs ctest, benchmarks, clang-tidy/cppcheck, lizard, cmake dep scan
        • parses include graph for architecture drift
        • emits build_report.json (raw, reproducible)
   -> codeforge upload build_report.json --api-url ... --api-key ...
   -> POST /api/projects/{id}/builds        (FastAPI)
        • validates the report (Pydantic)
        • persists raw metrics in PostgreSQL (kept so all derived scores are reproducible)
        • computes health categories + overall score
        • runs trend analysis across history
        • generates rule-based engineering insights
   -> GET /api/projects/{id}/*               (FastAPI)
   -> React dashboard (7 pages)
```

## 4. Existing coverage review

Every functional module requested (A–G) maps to a collector analyzer plus a
storage model plus API endpoints. The spec already defines the major tables,
the health-score weights, the trend vocabulary, the insight model, and the CI
integration.

## 5. Gaps the spec leaves open (identified by this analysis)

1. **Report ingestion security** — the spec has `POST /api/builds` but no
   authentication story. CODEFORGE adds an optional `X-API-Key` header
   (per-project shared secret) for ingestion and read access; disabled when no
   key is configured so it stays "basic auth if required".
2. **Reproducibility contract** — the collector must record the tool versions,
   raw tool exit codes, and raw output so the Health Score and trends can be
   recomputed. Spec asks for "keep raw metric data"; we make it explicit via
   `environment` JSONB on `builds` and full raw reports stored on demand.
3. **Anomaly detection** — not detailed in the spec. Implemented as two moving
   averages + Z-score on each numeric metric in the Trend Engine; outputs
   `IMPROVING / STABLE / DEGRADING / CRITICAL` plus `anomaly` flags.
4. **Configurable thresholds** — benchmark thresholds are specified; the Health
   Score "must be modular so weights and thresholds can be configured".
   Implemented as a settings model stored in DB (with defaults) so the backend
   can change weights without code changes.
5. **Build uniqueness / retries** — a rejected CI retry would create duplicate
   builds. The ingestion endpoint dedupes on `(project_id, commit_hash, unique_id)`
   supplied by the collector.
6. **Dev database** — PostgreSQL is required, but local verification on a
   plain laptop must not depend on Docker being up. `DATABASE_URL` is configurable
   and tests run on SQLite; production defaults to PostgreSQL.
7. **Graceful degradation** — clang-tidy/cppcheck/lizard may be missing on a
   machine. Analyzers detect availability and record `status: SKIPPED/UNSUPPORTED`
   instead of crashing (spec §19 requirement).

## 6. Technical risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| External C++ tools unavailable on evaluation machine | Medium | Graceful skip + meaningful status; analyzers are pluggable |
| Docker/Postgres not available for local dev | High | SQLite fallback via `DATABASE_URL`; same models/Alembic for both |
| Huge clang-tidy reports slowing ingestion | Medium | Deduplicate issues per build; single insert with dedupe key |
| Flaky detection false positives | Medium | Required state changes ≥ 2 over executions ≥ 3 before flagging |
| Weight/score drift across versions | Medium | Version the score formula; persist category scores; store raw data |
| Frontend/backend drift (API contract) | Medium | Single source of truth in OpenAPI (from FastAPI); typed frontend client |