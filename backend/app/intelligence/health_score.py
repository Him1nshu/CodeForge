"""Pure computation engine for the Engineering Health Score.

Design doc: docs/06-health-score.md.

This module contains NO database access. Given a snapshot of raw metrics it
returns category scores, the weighted overall score, the grade, the weights
actually used, and evidence (missing-data flags and sub-metrics) so every score
is reproducible and auditable.
"""

import math
from dataclasses import dataclass, field

FORMULA_VERSION = "1.0"

DEFAULT_WEIGHTS = {
    "build": 0.15,
    "code_quality": 0.20,
    "testing": 0.20,
    "performance": 0.15,
    "maintainability": 0.15,
    "architecture": 0.15,
}

GRADES = [(90, "EXCELLENT"), (75, "GOOD"), (60, "MODERATE"), (40, "POOR"), (0, "CRITICAL")]


def grade_from_score(score: float) -> str:
    for threshold, name in GRADES:
        if score >= threshold:
            return name
    return "CRITICAL"


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class HealthInput:
    """Raw metrics required by the engine (all sourced from DB rows)."""

    status: str = "UNKNOWN"
    duration_ms: int | None = None
    durations_history: list[int] = field(default_factory=list)
    compiler_warnings: int = 0

    issue_severity_counts: dict[str, int] = field(default_factory=dict)
    lines_of_code: int | None = None
    previous_issue_density: float | None = None

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    flaky_count: int = 0

    benchmark_pairs: list[tuple[float | None, float | None]] = field(default_factory=list)

    maintainability_index: float | None = None
    functions_above_threshold: int | None = None
    avg_function_complexity: float | None = None

    drift_score: float | None = None

    weights: dict[str, float] | None = None

    # --- derived helpers ---------------------------------------------------
    @property
    def weighted_issues(self) -> float:
        c = self.issue_severity_counts
        return float(c.get("critical", 0) * 3 + c.get("high", 0) * 2 + c.get("medium", 0) * 1.5 + c.get("low", 0))

    @property
    def issue_density(self) -> float | None:
        """Weighted issues per kLOC."""
        if self.lines_of_code and self.lines_of_code > 0:
            return self.weighted_issues / self.lines_of_code * 1000.0
        return None


@dataclass
class HealthResult:
    overall_score: float
    grade: str
    build_health: float
    code_quality: float
    testing: float
    performance: float
    maintainability: float
    architecture: float
    weights: dict[str, float]
    formula_version: str
    evidence: dict


# --------------------------------------------------------------------------
# Category functions
# --------------------------------------------------------------------------


def build_health(data: HealthInput) -> tuple[float, dict]:
    ev: dict = {"missing": data.status == "UNKNOWN"}
    if data.status not in ("SUCCESS", "PASSED"):
        return 0.0, {**ev, "reason": f"status={data.status}"}

    score = 100.0
    # Duration growth vs 4-build moving average of PREVIOUS builds.
    if data.duration_ms is not None and data.durations_history:
        ma = sum(data.durations_history) / len(data.durations_history)
        if ma > 0:
            growth = (data.duration_ms - ma) / ma * 100.0
            ev["duration_growth_pct"] = round(growth, 1)
            if growth > 0:
                score -= min(40.0, 20.0 * (growth // 10.0))
    # Compiler warnings trend vs a soft baseline of 0.
    ev["compiler_warnings"] = data.compiler_warnings
    score -= min(20.0, (data.compiler_warnings // 50) * 5.0)
    return _clip(score), dict(ev)


def code_quality(data: HealthInput) -> tuple[float, dict]:
    density = data.issue_density
    missing = density is None
    ev: dict = {"missing": missing, "issue_density": density}

    if density is None:
        density_term = _clip(100.0 - data.weighted_issues * 2.0)
    else:
        density_term = _clip(100.0 - 2.0 * min(density, 50.0))

    delta_term = 100.0  # neutral when there is no previous build
    if data.previous_issue_density is not None and density is not None:
        delta = density - data.previous_issue_density
        ev["issue_density_delta"] = round(delta, 3)
        delta_term = _clip(100.0 - delta * 20.0)
        score = 0.7 * density_term + 0.3 * delta_term
    else:
        score = density_term
    return _clip(score), dict(ev)


def testing(data: HealthInput) -> tuple[float, dict]:
    total_run = data.passed + data.failed
    if total_run == 0:
        return 0.0, {"missing": True, "reason": "no tests executed"}
    pass_rate = data.passed / total_run
    all_tests = total_run + data.skipped
    skip_penalty = 1.0 - 0.02 * (data.skipped / all_tests) if all_tests else 1.0
    score = pass_rate * 100.0 * skip_penalty
    score -= 10.0 * data.flaky_count
    return _clip(score), {
        "missing": False,
        "pass_rate": round(pass_rate, 4),
        "flaky_count": data.flaky_count,
    }


def performance(data: HealthInput) -> tuple[float, dict]:
    scores: list[float] = []
    ev: dict = {"missing": len(data.benchmark_pairs) == 0}
    for prev, cur in data.benchmark_pairs:
        if not prev or not cur or prev <= 0:
            continue
        ratio = prev / cur
        if ratio >= 1.0:
            sc = 70.0 + 30.0 * math.tanh(4.0 * (ratio - 1.0))
        else:
            sc = max(20.0, 100.0 - 250.0 * (1.0 - ratio))
        scores.append(sc)
    if not scores:
        # No benchmarks is not a defect: neutral category.
        return 50.0, ev
    mean = sum(scores) / len(scores)
    ev["benchmark_count"] = len(scores)
    return _clip(mean), dict(ev)


def maintainability(data: HealthInput) -> tuple[float, dict]:
    ev: dict = {"missing": data.maintainability_index is None}
    complexity_factor = 100.0
    if data.functions_above_threshold is not None:
        complexity_factor -= 10.0 * math.ceil(data.functions_above_threshold / 5.0)
        ev["functions_above_threshold"] = data.functions_above_threshold
    if data.avg_function_complexity is not None and data.avg_function_complexity > 10.0:
        complexity_factor -= 10.0
        ev["avg_function_complexity"] = data.avg_function_complexity

    if data.maintainability_index is None:
        return _clip(complexity_factor), dict(ev)
    score = 0.7 * _clip(data.maintainability_index) + 0.3 * _clip(complexity_factor)
    ev["maintainability_index"] = data.maintainability_index
    return _clip(score), dict(ev)


def architecture(data: HealthInput) -> tuple[float, dict]:
    if data.drift_score is None:
        return 50.0, {"missing": True}
    return _clip(100.0 - data.drift_score), {"missing": False, "drift_score": data.drift_score}


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

_CATEGORY_FUNCS = {
    "build": build_health,
    "code_quality": code_quality,
    "testing": testing,
    "performance": performance,
    "maintainability": maintainability,
    "architecture": architecture,
}


def compute_health(data: HealthInput) -> HealthResult:
    """Compute category + overall scores for one build snapshot."""
    weights = {**DEFAULT_WEIGHTS}
    if data.weights:
        weights.update(data.weights)

    categories: dict[str, float] = {}
    evidence: dict[str, dict] = {}
    for name, func in _CATEGORY_FUNCS.items():
        value, ev = func(data)
        categories[name] = round(value, 2)
        evidence[name] = ev

    overall = round(
        sum(categories[name] * weights[name] for name in _CATEGORY_FUNCS), 2
    )

    # A failed (or fully missing) build cannot be rescued by other categories:
    # cap the headline score at the build weight scaled by the hard-failure
    # penalty factor so the failure dominates the grade.
    if categories["build"] == 0.0:
        overall = round(weights["build"] * 100.0 * 0.85, 2)

    ev_order = ["build", "code_quality", "testing", "performance", "maintainability", "architecture"]
    return HealthResult(
        overall_score=overall,
        grade=grade_from_score(overall),
        build_health=categories["build"],
        code_quality=categories["code_quality"],
        testing=categories["testing"],
        performance=categories["performance"],
        maintainability=categories["maintainability"],
        architecture=categories["architecture"],
        weights={k: round(v, 4) for k, v in weights.items()},
        formula_version=FORMULA_VERSION,
        evidence={"categories": {k: evidence[k] for k in ev_order}},
    )
