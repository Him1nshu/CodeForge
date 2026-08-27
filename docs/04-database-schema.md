# BuildPulse — PostgreSQL Schema

Normalized relational schema. All tables have a UUID `id` PK
(`postgresql.UUID(as_uuid=True)`; SQLite-mapped behind SQLAlchemy so tests
can run anywhere), and `created_at` timestamps.

## Entity relationships

```text
projects 1───n builds
builds   1───n build_metrics (1:1 in practice, kept for history snapshots)
builds   1───n code_metrics
builds   1───n static_analysis_issues
builds   1───n test_results
builds   1───n benchmarks
builds   1───n dependencies
builds   1───n architecture_metrics
builds   1───n architecture_violations
builds   1───1 health_scores
builds   1───n engineering_insights
```

## Tables

### projects
| column | type | notes |
| --- | --- | --- |
| id | uuid pk | |
| project_name | varchar(200) not null, unique, indexed | |
| repository_url | varchar(500) | |
| branch | varchar(200) | default `main` |
| build_command | varchar(500) | |
| test_command | varchar(500) | |
| benchmark_command | varchar(500) | |
| binary_path | varchar(500) | |
| analysis_tools | jsonb | enabled tool list, arch layer mapping |
| health_config | jsonb | overridable weights/thresholds |
| api_key_hash | varchar(100) nullable | optional ingest/read key (sha256) |
| created_at / updated_at | timestamptz | |

Indexes: `project(name)` unique.

### builds
| column | type | notes |
| --- | --- | --- |
| id | uuid pk | |
| project_id | uuid fk → projects | |
| build_number | int | monotonically increasing per project |
| status | varchar(20) | `SUCCESS` / `FAILURE` / `ABORTED` / `UNKNOWN` |
| start_time / end_time | timestamptz | |
| duration_ms | bigint | end − start |
| commit_hash | varchar(64) | |
| branch | varchar(200) | |
| commit_message | text | |
| commit_author | varchar(200) | |
| commit_timestamp | timestamptz | |
| changed_files | int | |
| lines_added / lines_removed | int | |
| compiler_warnings | int | |
| compiler_errors | int | |
| build_retries | int | |
| collector_run_id | varchar(100) | dedupe key input |
| environment | jsonb | OS, compiler, tool versions |
| raw_report | jsonb nullable | full `build_report.json` for reproducibility |
| created_at | timestamptz | |

Indexes: `(project_id, build_number)`, `(project_id, commit_hash)`,
`(project_id, created_at)`, `(project_id, collector_run_id)`.

### build_metrics
| column | type |
| --- | --- |
| id uuid pk, build_id fk unique | |
| binary_size bigint, binary_size_change bigint, pct_binary_growth float |
| artifact_count int, artifact_paths jsonb |

### code_metrics
| column | type |
| --- | --- |
| id uuid pk, build_id fk unique | |
| cyclomatic_complexity_total int, avg_function_complexity float, max_function_complexity int |
| functions_above_threshold int, complexity_threshold int |
| maintainability_index float, lines_of_code int, avg_function_length float, functions int |
| top_complex_functions jsonb | `<n>` entries: {file, function, complexity, nc} |

### static_analysis_issues
| column | type |
| --- | --- |
| id uuid pk, build_id fk | |
| tool, file, rule, message, category varchar |
| line int, severity varchar(20) `critical/high/medium/low` |
| `UNIQ(build_id, tool, file, line, rule)` |

Index: `(build_id)`.

### test_results
| column | type |
| --- | --- |
| id uuid pk, build_id fk | |
| suite varchar(200), name varchar(500), status varchar(20) `passed/failed/skipped` |
| duration_ms float |
| `UNIQ(build_id, suite, name)` |

Index: `(build_id, name)`.

### benchmarks
| column | type |
| --- | --- |
| id uuid pk, build_id fk | |
| name varchar(200), mean_ms float, median_ms float, stddev_ms float, cpu_ms float, throughput float, iterations int |
| `UNIQ(build_id, name)` |

### dependencies
| column | type |
| --- | --- |
| id uuid pk, build_id fk | |
| name varchar(200), version varchar(100), type varchar(50) |
| change varchar(20) `added/removed/updated/unchanged`, previous_version varchar(100) |

Index: `(build_id, name)`.

### architecture_metrics
| column | type |
| --- | --- |
| id uuid pk, build_id fk unique | |
| drift_score float (0–100), layer_violations int, cyclic_dependencies int, unexpected_coupling int |
| domain_direction_violations int, module_count int, edge_count int |
| dependency_graph jsonb | {nodes:[id,module,layer], edges:[source,target]} |

### architecture_violations
| column | type |
| --- | --- |
| id uuid pk, build_id fk | |
| violation_type varchar(40) `layer/cycle/coupling/direction` |
| source_module, target_module, source_layer, target_layer, message |
| approval varchar(20) `open/approved/wontfix` default open |

### health_scores
| column | type |
| --- | --- |
| id uuid pk, build_id fk unique, project_id fk | |
| overall_score float, build_health float, code_quality float, testing float, performance float, maintainability float, architecture float |
| grade varchar(20), formula_version varchar(10), weights jsonb |

Index: `(project_id, build_id)`.

### engineering_insights
| column | type |
| --- | --- |
| id uuid pk, build_id fk, project_id fk | |
| priority varchar(20) `info/warning/high/critical`, category varchar(50), title varchar(300) |
| message text, recommendation text, evidence jsonb |

Index: `(project_id, priority)`.

## Rationale for key choices

- **build_metrics / code_metrics / architecture_metrics are 1:1 with builds**
  but separate tables: clean aggregates, per-build snapshots, and bulk
  time-series queries never need to read bulky rows (e.g. issues).
- **Raw report stored** on `builds.raw_report` enables re-computation of any
  score, satisfying the reproducibility requirement.
- **Qualitative `grade`** on health_scores is derived, never entered.
- **JSONB only for genuinely nested data** (top complex functions, dep graph,
  environment, artifacts) — everything queryable is a real column.