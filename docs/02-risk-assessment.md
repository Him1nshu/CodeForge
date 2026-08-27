# BuildPulse — Risk Assessment

Severity = Likelihood × Impact (H/3, M/2, L/1 on each axis → 1..9).

| # | Risk | Likelihood | Impact | Severity | Mitigation / Evidence gate |
| --- | --- | --- | --- | --- | --- |
| R1 | External C++ tools (clang-tidy, cppcheck, lizard, gcov) missing on the build host | High | Medium | 6 | Analyzer base class detects executables; missing tools produce `SKIPPED` status with reason, never crash; collector still emits a full report |
| R2 | PostgreSQL unreachable during local dev/eval | High | Medium | 6 | `DATABASE_URL` env override; SQLite for tests/dev; Alembic migrations runnable on both |
| R3 | Duplicate builds (CI retries, re-runs) corrupt history/trends | Medium | High | 6 | Ingestion dedupes on `(project_id, commit_hash, collector_run_id)`; upsert for test_results/issues |
| R4 | Health Score opaque / unreproducible | Medium | High | 6 | Raw metrics persisted; category scores persisted per build; formula versioned; weights configurable from DB |
| R5 | Very large static-analysis reports slow ingestion or blow JSON | Low | Medium | 4 | Issue dedupe key `(build_id, tool, file, line, rule)`; batch inserts; report upload streamed as JSON body with size guard |
| R6 | Flaky-test detector false positives | Medium | Medium | 4 | Requires ≥3 executions and ≥2 state changes before flagging |
| R7 | Frontend/backend contract drift | Medium | Medium | 4 | FastAPI is the OpenAPI source of truth; frontend uses a generated, typed client; contract tests in backend CI step |
| R8 | Clickjacking/unauthorized build upload | Low | High | 3 | Optional per-project API key checked via `X-API-Key` on ingest/read; configurable in settings |
| R9 | Architect module mapping wrong (drift scoring misleading) | Medium | Low | 3 | Module/layer mapping is data-driven config; violations always cite the include `source -> target` edge so claims are checkable |
| R10 | C++ toolchain differences skew binary size / times | Medium | Low | 3 | Environment JSONB records toolchain + OS + compiler flags; comparisons flagged when environment changes |

**Policy.** Every risk above has an evidence gate in Phase 2–5 unit/integration
tests. New analyzers register themselves; the collector summary lists every tool
with its resolved status so nothing is silently missing.