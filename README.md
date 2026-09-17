# CODEFORGE

CODEFORGE is an engineering intelligence platform for tracking the health of C++ projects across builds. It combines a FastAPI backend, a React dashboard, and a collector CLI that analyzes a repository and uploads a `build_report.json`.

## Repository Layout

- `backend/` - FastAPI application, SQLAlchemy models, Alembic migrations, and tests
- `collector/` - `codeforge` CLI and repository analyzers
- `frontend/` - React, TypeScript, Vite, and Tailwind dashboard
- `sample-projects/` - sample C++ and Java project histories
- `scripts/` - end-to-end evaluation scripts
- `docs/` - architecture, API, schema, and roadmap documentation

## Prerequisites

Install the following before starting:

- Python 3.11 or newer
- Node.js 18 or newer and npm
- Git
- PostgreSQL 14 or newer for a PostgreSQL-backed setup
- A C++ toolchain such as `g++` and CMake if you want to run the sample collector evaluation

The commands below use PowerShell on Windows. Equivalent shell commands work on macOS and Linux with the usual virtual-environment activation syntax.

## Quick Start With SQLite

SQLite is the quickest way to run CODEFORGE locally and does not require a database server.

### 1. Clone the repository

```powershell
git clone https://github.com/vishwa-10147/CODEFORGE.git
cd CODEFORGE
```

### 2. Create and activate a Python environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install --editable collector
```

If PowerShell blocks activation, run this once for the current user, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Configure the backend

The backend defaults to PostgreSQL. Set the database URL to a local SQLite file for this quick start:

```powershell
$env:CODEFORGE_DATABASE_URL = "sqlite:///./codeforge.db"
```

Environment variables use the `CODEFORGE_` prefix. Common settings include:

- `CODEFORGE_DATABASE_URL` - SQLAlchemy URL; defaults to PostgreSQL
- `CODEFORGE_GLOBAL_API_KEY` - optional global API key
- `CODEFORGE_CORS_ORIGINS` - allowed frontend origins
- `CODEFORGE_DEBUG` - enable debug mode

You can also put these values in `backend\.env`. When running commands from `backend`, a relative SQLite URL such as `sqlite:///./codeforge.db` creates the file in `backend`.

### 4. Run database migrations

```powershell
Set-Location backend
python -m alembic upgrade head
```

### 5. Start the API

Keep this terminal open:

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at <http://localhost:8000>. Check <http://localhost:8000/healthz> and open the interactive API documentation at <http://localhost:8000/docs>.

### 6. Start the frontend

Open a second terminal from the repository root and activate the same environment only if needed for your workflow:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the backend at `http://localhost:8000`.

## Create a Project and Upload a Report

With the API running, create a project. PowerShell's `Invoke-RestMethod` returns the created project, including its UUID:

```powershell
$project = Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/projects `
  -ContentType "application/json" `
  -Body '{"project_name":"AnalyticEngine","description":"sample project"}'

$project | Format-List
$project.id
```

Create a starter collector configuration in a project repository, then collect a report:

```powershell
Set-Location sample-projects\analytic-engine
codeforge init
codeforge collect --repo . --out build_report.json
```

Upload the report using the project UUID from the previous command:

```powershell
codeforge upload `
  --api http://localhost:8000 `
  --project $project.id `
  --report .\build_report.json
```

Refresh the dashboard to see the project and its build metrics. The collector can also be run directly as a Python module:

```powershell
python -m codeforge.cli --version
```

Use `codeforge config --repo <path>` to inspect the effective configuration. Analyzer names accepted by `--skip` are `git`, `build`, `tests`, `static_analysis`, `complexity`, `benchmarks`, `dependencies`, and `architecture`.

## PostgreSQL Setup

For a PostgreSQL-backed local environment, create a database and user, then set the backend URL before migrating:

```powershell
$env:CODEFORGE_DATABASE_URL = "postgresql+psycopg://codeforge:codeforge@localhost:5432/codeforge"
Set-Location backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The default URL is the same value. Ensure that PostgreSQL is running and that the `codeforge` database and user exist before running the migration.

## Running Tests and Checks

Backend tests:

```powershell
Set-Location backend
python -m pytest
python -m ruff check .
```

Collector tests:

```powershell
Set-Location collector
python -m pytest
python -m ruff check .
```

Frontend type check and production build:

```powershell
Set-Location frontend
npm run lint
npm run build
```

## End-to-End Sample Evaluation

The evaluation script replays the C++ sample releases, runs the collector, uploads each report to a temporary SQLite-backed API, and prints the health trend. From an activated environment with the backend dependencies and editable collector installed:

```powershell
Set-Location scripts
python .\eval_sample.py
```

The evaluation requires a working `g++` installation and Git. It starts its own API on port `8777`, creates `backend\eval.db`, and removes its temporary working tree when it finishes.

## API Overview

- `GET /healthz` - service health check
- `GET /docs` - Swagger UI
- `GET /api/projects` - list projects
- `POST /api/projects` - create a project
- `POST /api/projects/{project_id}/builds` - ingest a collector report
- `GET /api/projects/{project_id}/health` - current health score
- `GET /api/projects/{project_id}/health/history` - health history
- `GET /api/projects/{project_id}/metrics` - project metrics
- `GET /api/projects/{project_id}/trends` - detected trends
- `GET /api/projects/{project_id}/insights` - generated insights
- `GET /api/projects/{project_id}/architecture` - architecture analysis

For the complete request and response contract, use the running Swagger documentation or see [docs/05-api-contracts.md](docs/05-api-contracts.md).

## Configuration File

The collector reads `codeforge.toml` from the repository passed to `codeforge collect`. A minimal C++ configuration looks like this:

```toml
[project]
name = "MyCppProject"
language = "cpp"
branch = "main"
build_command = "cmake -S . -B build && cmake --build build -j"
test_command = "ctest --test-dir build --output-on-failure"
benchmark_command = "./build/bin/benchmarks"
binary_path = "build/bin/sample_app"

[analyzers.complexity]
tool = "auto"
complexity_threshold = 15
```

Analyzer tools that are unavailable are reported as skipped or unsupported where applicable, so a report can still be generated while a repository is being configured.

## Troubleshooting

- **Frontend requests fail:** verify the backend is running on port 8000. The Vite proxy is configured for that port.
- **Database connection fails:** check `CODEFORGE_DATABASE_URL`, PostgreSQL availability, and that migrations have been applied.
- **`codeforge` is not recognized:** activate the virtual environment and run `python -m pip install --editable collector` again.
- **Collector build or test analysis is skipped:** confirm the commands in `codeforge.toml` work from the repository root and that the required build tools are on `PATH`.
- **Port already in use:** start Uvicorn on another port and update the Vite proxy target in `frontend\vite.config.ts` if the frontend must use that port.

## Documentation

- [Architecture analysis](docs/01-architecture-analysis.md)
- [Risk assessment](docs/02-risk-assessment.md)
- [Final architecture](docs/03-final-architecture.md)
- [Database schema](docs/04-database-schema.md)
- [API contracts](docs/05-api-contracts.md)
- [Health score](docs/06-health-score.md)
- [Development roadmap](docs/07-roadmap.md)
