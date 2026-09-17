# CODEFORGE — Engineering Health Score

Transparent, configurable, reproducible from raw data.

## Formula (documented reference)

```text
Health = W_build·BuildHealth
       + W_code·CodeQuality
       + W_test·Testing
       + W_perf·Performance
       + W_main·Maintainability
       + W_arch·Architecture

Default weights:
W_build = 0.15, W_code = 0.20, W_test = 0.20,
W_perf  = 0.15, W_main = 0.15, W_arch = 0.15
```

Weights sum to 1.0 and live in `projects.health_config` (overridable); the
weight set actually used is stored with each `health_scores` row so a formula
change never silently re-interprets old scores.

Grades: `90–100 EXCELLENT, 75–89 GOOD, 60–74 MODERATE, 40–59 POOR, 0–39 CRITICAL`.

## Category definitions (each normalized to 0–100, higher = better)

### BuildHealth (15%)
- Base 100 for status `SUCCESS`, 0 for `FAILURE`/`ABORTED`.
- −20 per 10% build-duration growth vs. 4-build moving average (max −40).
- −5 per 50 compiler warnings vs. previous stable build (max −20).
- Clipped 0–100.

### CodeQuality (20%)
- Base 100 − 2 × normalized issue density:
  `issues per 1k LOC` capped at 50 → `density_score = max(0, 100 − 2·density)`.
- Severity weighting: `issues = critical·3 + high·2 + medium·1.5 + low·1`.
- Category= 0.7·density_score + 0.3·Δ vs previous build (0 for missing).

### Testing (20%)
- `pass_rate = passed / (passed + failed)[·(1 − 0.02·skipped_ratio)]`.
- Start from pass_rate·100; −10 per flaky test flagged (min 0).
- No tests recorded → 0 with `missing_data` flag in evidence.

### Performance (15%)
- Evaluate each benchmark: `ratio = prev_mean / current_mean`.
  Ratio ≥ 1.0 (no regression) → saturating 70 + 30·tanh(4·(ratio−1)).
  Ratio < 1.0 → penalty: `100 − 250·(1−ratio)` clamped to [20, 70].
- Category = mean of per-benchmark scores; no benchmarks → neutral 50.

### Maintainability (15%)
- `maintainability_index` (MI, 0–100 from lizard): scaled directly.
- Complexity factor: `functions_above_threshold` penalty
  `−10·ceil(n/5)`; avg function complexity > 10 → −10.
- `maintainability = clip(0.7·MI + 0.3·complexity_factor, 0, 100)`.

### Architecture (15%)
- `drift_score` (0 = no drift, 100 = severe drift) computed by drift engine.
- `architecture = 100 − drift_score` (minus minor layer alignment info).

## Reproducibility

1. All inputs come from DB raw rows (build_metrics, code_metrics, issues,
   tests, benchmarks, architecture_metrics).
2. The computed category + overall scores are **persisted** on `health_scores`
   at ingestion time; the formula version is recorded.
3. Re-running scoring for a stored build with identical raw data reproduces
   identical scores — verified by an integration test for every category
   (pure function + property check on stored row).

## Failure/missing-data policy

Any missing category gets an explicit `missing_data` evidence flag; it is
scored 0 for build, but **neutral (50)** for performance (no benchmarks is not
a defect) — never silently excluded from the weighted sum.

**Failed-build override (added during implementation):** when build status is
`FAILURE`/`ABORTED`/`UNKNOWN` the category is 0 and the **overall** score is
capped at `W_build·100·0.85` (~12.8 with default weights) — a failed build
cannot be rescued by healthy code/tests/architecture, so the headline grade is
dominated by the failure. The category scores remain visible for diagnosis.

**Drift layering rule (implementation precision):** an include edge is a
*layer violation* when it goes backwards in layer order (presentation→……→infrastructure)
_or_ skips one or more intermediate layers; skipped edges also count separately
as `unexpected_coupling`. Cycles add `cyclic_dependencies`; score = 4·layer
+ 3·jump + 3·offending modules + 6·cycle-members, capped at 100.

**Health-drop insight thresholds:** single-build drop ≥15 pts → critical,
≥8 pts → high (implementation verified against the 5-version story).