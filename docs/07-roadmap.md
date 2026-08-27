# BuildPulse — Development Roadmap

Phases mirror the specification; each phase ends with a verifiable acceptance
gate. Work is incremental: a working end-to-end MVP ships before advanced
features.

## Phase 1 — Foundations & running backend
- Monorepo scaffold, Docker environment, PostgreSQL compose profile.
- Backend: settings, DB session, Alembic init, all base models, dependency
  wiring, Swagger on `/docs`.
- Frontend: Vite + React + TS + Tailwind scaffold, sidebar layout, typed API client.
- **Gate:** `pytest backend/tests -x` green; `python -m uvicorn app.main` boots; frontend `npm run build` passes.

## Phase 2 — Projects & build ingestion (MVP core)
- Project CRUD; report ingestion endpoint with dedupe; raw report persistence.
- Build number assignment; environment JSONB.
- **Gate:** integration test posts a `build_report.json` and reads it back; duplicate posts return 409.

## Phase 3 — Analysis modules in backend
- Health Score Engine (+ tests for every category & formula versioning).
- Trend Analysis Engine (moving average, Z-score anomaly, direction).
- Insights Engine (rule-based, priorities INFO..CRITICAL).
- **Gate:** fuzzy score/trend unit tests; end-to-end test over seeded 5-version history.

## Phase 4 — Deep analysis services
- Benchmark regression detection (warn >10%, critical >25%); dependency churn;
  architecture drift graph + violation detection.
- **Gate:** seeded degradation is detected with correct severity labels.

## Phase 5 — Collector CLI + analyzers
- `buildpulse collect` runs tools, writes `build_report.json`; `buildpulse upload` POSTs it.
- Graceful SKIPPED/UNSUPPORTED status for missing tools.
- **Gate:** collect on the sample project produces a valid report; upload lands in DB.

## Phase 6 — Frontend dashboard (7 pages)
- Overview (health gauge anim, score history line, metric cards) wired to API.
- Build Analytics, Code Quality, Test Intelligence, Performance, Architecture
  (graph), Build History (searchable, drill-down).
- **Gate:** every chart consumes a live endpoint; empty/error/loading states; build passes.

## Phase 7 — CI integration & evaluation
- GitHub Actions `buildpulse-analysis.yml`; sample-project experiments v1..v5;
- Evaluation framework generating the version comparison table from real metrics.
- **Gate:** table values traceable to collected metrics; README runnable from clone.

## Current status (session 2026-08-27)
- Backend fully implemented and verified: `ruff check` clean; 44/44 `pytest` green
  (pure engines + API integration incl. the 5-version degradation story); Alembic
  `0001_initial` schema upgrade + downgrade verified on SQLite.
- Phase 1–2 (Docker compose profile pending daemon), 3, and 4 (drift graph wired
  into ingestion) are done. Next: Phase 5 collector CLI + analyzers, then the
  sample C++ project v1..v5, frontend, CI workflow, and evaluation docs.
- Decision deltas introduced while implementing (now authoritative):
  - A failed/UNKNOWN build caps the overall score at `W_build·100·0.85` — other
    categories can never rescue a headline grade (health-score tests encode this).
  - Drift: an edge counts as a *layer violation* when it goes backwards OR skips
    one or more layers; jumps count separately as `unexpected_coupling`.
  - Trend "higher is better" thresholds raised to match pass-rate scale
    (IMPROVING ≥3%, DEGRADING ≤−5%, CRITICAL ≤−10%).
  - Insights health-drop severities: critical ≥15 pts, high ≥8 pts.
  - Projects table column is `project_name` (was `name` in doc 04).