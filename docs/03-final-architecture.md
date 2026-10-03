# CODEFORGE — Final Architecture

## 1. Decision summary

| Concern | Decision | Rationale |
| --- | --- | --- |
| Language | Python 3.12+ (backend/collector), TypeScript (frontend), C++ (samples) | Spec-mandated |
| API framework | FastAPI + Pydantic v2 | OpenAPI + Swagger free, type-safe validation |
| Persistence | PostgreSQL (prod), SQLite (tests/dev fallback) via `DATABASE_URL` | Same SQLAlchemy models + Alembic for both |
| Ingestion | REST `POST /api/projects/{id}/builds` carrying `build_report.json` | Simpler than Celery+GCS; reports are ≤ a few MB |
| Compute | Collector runs where the build runs (GitHub Actions); backend only stores/serves | Natural fit; no queue needed in v1 |
| Auth | Optional `X-API-Key` per project (disabled by default) | "Basic auth if required" |
| Extensibility | Analyzer plugin pattern on both collector (metric => report dict) and intelligence (report + history => derived data) | New analyzers drop in |

## 2. Layered architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ Presentation layer    React 18 + Vite + Tailwind + Recharts   │
│                       7 pages, typed API client               │
├──────────────────────────────────────────────────────────────┤
│ API layer            FastAPI routers (thin)                   │
│                       ingestion, query, scoring endpoints     │
├──────────────────────────────────────────────────────────────┤
│ Application layer     services/                               │
│   builders  → BuildService (save report, dedupe)              │
│   scoring   → HealthScoreEngine (weighted categories)         │
│   analytics → TrendEngine (moving avg, Z-score, direction)    │
│   insights  → InsightsEngine (rule-based, priority)           │
│   arch      → ArchitectureService (drift graph, violations)   │
├──────────────────────────────────────────────────────────────┤
│ Domain/data layer     models/ (SQLAlchemy 2.0 typed)          │
│                       Alembic migrations, JSONB raw metrics   │
│                       PostgreSQL / SQLite                     │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│ Collector (separate process, runs at build time)              │
│   analyzers / build, static, complexity, tests, benchmarks,   │
│   dependencies, architecture   ->  build_report.json          │
│   CLI: codeforge collect / upload                            │
└──────────────────────────────────────────────────────────────┘
```

## 3. Monorepo layout

```text
codeforge/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── api/             routers (projects, builds, health, metrics,
│   │   │                    trends, insights, architecture, benchmarks, tests)
│   │   ├── core/            settings, db, security, logging
│   │   ├── models/          SQLAlchemy models (1 file per aggregate)
│   │   ├── schemas/         Pydantic request/response schemas
│   │   ├── services/        build save, scoring, trends, insights, architecture
│   │   ├── intelligence/    health_score.py, trends.py, insights.py, drift.py
│   │   └── main.py
│   ├── migrations/          Alembic
│   ├── tests/               unit + integration (SQLite-backed)
│   ├── requirements.txt
│   └── Dockerfile
├── collector/
│   ├── codeforge/
│   │   ├── analyzers/       build.py, static.py, complexity.py, tests.py,
│   │   │                    benchmarks.py, dependencies.py, architecture.py
│   │   ├── collectors/      cmake/gcc tool discovery
│   │   ├── reporters/       report writer, uploader
│   │   └── cli.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      ui/ (button, card, gauge, charts), layout
│   │   ├── pages/           Overview, BuildAnalytics, CodeQuality, Tests,
│   │   │                    Performance, Architecture, BuildHistory
│   │   ├── hooks/           useApi, useHealth
│   │   ├── services/        api client (typed)
│   │   ├── types/           API types
│   │   └── App.tsx
│   └── package.json
├── sample-projects/         C++ demo: app v1..v5 + CMake
├── infrastructure/
│   ├── docker-compose.yml
│   └── github-actions/      codeforge-analysis.yml
├── docs/
└── README.md
```

## 4. Key design properties

- **Metric collection is separated from metric analysis**: the collector never
  computes health, trends, or insights; the backend recomputes derived data
  from raw records every time a build is ingested. This makes the pipeline
  reproducible and lets analyzers be added without touching scoring.
- **Analysis logic is separated from API controllers**: routers only marshal
  request/schema; all logic lives in `services/` and `intelligence/`.
- **Raw data is kept**: reports, tool output (optional), environment JSONB —
  so score math can be audited and re-run.
- **All numeric history is comparable across builds** via `build_id` + `created_at`.