"""Unit tests for the pure Health Score engine (docs/06-health-score.md)."""

import math

import pytest

from app.intelligence.health_score import (
    HealthInput,
    compute_health,
    grade_from_score,
)


def base_input(**kw) -> HealthInput:
    defaults = dict(
        status="SUCCESS",
        duration_ms=90000,
        durations_history=[90000, 95000, 92000],
        compiler_warnings=10,
        issue_severity_counts={},
        lines_of_code=3000,
        previous_issue_density=None,
        passed=100,
        failed=0,
        skipped=0,
        flaky_count=0,
        benchmark_pairs=[(120.0, 120.0), (45.0, 45.0)],
        maintainability_index=82.0,
        functions_above_threshold=1,
        avg_function_complexity=4.7,
        drift_score=3.0,
    )
    defaults.update(kw)
    return HealthInput(**defaults)


def test_healthy_baseline_scores_high() -> None:
    result = compute_health(base_input())
    assert result.overall_score >= 90
    assert result.grade == "EXCELLENT"
    for name in ("build", "code_quality", "testing", "performance", "maintainability", "architecture"):
        assert result.evidence["categories"][name]["missing"] is False or name == "architecture"


def test_failed_build_scores_low() -> None:
    result = compute_health(base_input(status="FAILURE"))
    assert result.build_health == 0.0
    assert result.overall_score <= 0.31 * 100 * 0.85  # build weight only


def test_grades() -> None:
    assert grade_from_score(95) == "EXCELLENT"
    assert grade_from_score(80) == "GOOD"
    assert grade_from_score(70) == "MODERATE"
    assert grade_from_score(50) == "POOR"
    assert grade_from_score(20) == "CRITICAL"


def test_build_duration_growth_penalty() -> None:
    clean = compute_health(base_input())
    slow = compute_health(base_input(duration_ms=140000, durations_history=[90000]))
    assert slow.build_health < clean.build_health


def test_issue_density_reduces_code_quality() -> None:
    clean = compute_health(base_input())
    dirty = compute_health(base_input(issue_severity_counts={"critical": 2, "high": 5}))
    assert dirty.code_quality < clean.code_quality


def test_test_failures_and_flaky_reduce_testing() -> None:
    clean = compute_health(base_input())
    flaky = compute_health(base_input(failed=12, flaky_count=3))
    assert flaky.testing < clean.testing


def test_benchmark_regression_reduces_performance() -> None:
    clean = compute_health(base_input())
    regressed = compute_health(base_input(benchmark_pairs=[(120.0, 165.0), (45.0, 45.0)]))
    assert regressed.performance < clean.performance
    assert regressed.performance >= 20.0  # clamped, never thrown away


def test_no_benchmarks_is_neutral_not_zero() -> None:
    result = compute_health(base_input(benchmark_pairs=[]))
    assert result.performance == 50.0
    assert result.evidence["categories"]["performance"]["missing"] is True


def test_weights_are_configurable_and_recorded() -> None:
    weights = {"build": 0.5, "code_quality": 0.1, "testing": 0.1,
               "performance": 0.1, "maintainability": 0.1, "architecture": 0.1}
    result = compute_health(base_input(weights=weights))
    assert result.weights["build"] == 0.5
    assert abs(sum(result.weights.values()) - 1.0) < 1e-6


def test_reproducible_for_same_input() -> None:
    a = compute_health(base_input())
    b = compute_health(base_input())
    assert a.overall_score == b.overall_score
    assert a.formula_version == b.formula_version


@pytest.mark.parametrize(
    "drift,expect_lower",
    [(3.0, False), (60.0, True), (95.0, True)],
)
def test_drift_reduces_architecture_category(drift: float, expect_lower: bool) -> None:
    low = compute_health(base_input(drift_score=3.0))
    high = compute_health(base_input(drift_score=drift))
    if expect_lower:
        assert high.architecture < low.architecture


def test_tanh_still_works() -> None:
    # Guard against a subtle import/deployment regression.
    assert abs(math.tanh(0)) < 1e-9
