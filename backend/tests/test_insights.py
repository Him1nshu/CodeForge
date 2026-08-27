"""Unit tests for the rule-based insights engine."""

from app.intelligence.health_score import HealthInput, compute_health
from app.intelligence.insights import InsightsContext, generate_insights
from app.intelligence.trends import BenchmarkRegression


def _ctx(**kw) -> InsightsContext:
    defaults = dict(
        build_number=11,
        health=compute_health(
            HealthInput(status="SUCCESS", passed=100, failed=0, maintainability_index=80.0)
        ),
        previous_health=None,
        status="SUCCESS",
        trends=[],
        passed=100,
        failed=0,
        skipped=0,
        flaky_tests=[],
        benchmark_regressions=[],
        deps_added=0,
        deps_removed=0,
        deps_updated=0,
        functions_above_threshold=2,
        previous_functions_above_threshold=2,
        drift_score=5.0,
    )
    defaults.update(kw)
    return InsightsContext(**defaults)


def test_healthy_build_emits_informational_insight() -> None:
    insights = generate_insights(_ctx())
    assert insights
    assert insights[0].priority == "info"


def test_build_failure_is_critical() -> None:
    insights = generate_insights(_ctx(status="FAILURE"))
    critical = [i for i in insights if i.priority == "critical"]
    assert any("failed" in i.title.lower() for i in critical)


def test_benchmark_regression_emits_high_critical() -> None:
    insights = generate_insights(
        _ctx(benchmark_regressions=[
            BenchmarkRegression("vector_processing", 120.0, 165.0, 37.5, "CRITICAL")
        ])
    )
    assert any(i.category == "performance" and i.priority == "critical" for i in insights)


def test_flaky_tests_flagged() -> None:
    insights = generate_insights(
        _ctx(flaky_tests=["test_network"], benchmark_regressions=[])
    )
    assert any("flaky" in i.title.lower() for i in insights)


def test_dependency_churn_info() -> None:
    insights = generate_insights(_ctx(deps_added=1, deps_updated=2))
    assert any(i.category == "dependencies" for i in insights)


def test_large_health_drop_is_critical() -> None:
    good = compute_health(
        HealthInput(status="SUCCESS", passed=100, failed=0, maintainability_index=80.0)
    )
    poor = compute_health(
        HealthInput(status="SUCCESS", passed=30, failed=70, maintainability_index=40.0)
    )
    insights = generate_insights(_ctx(health=poor, previous_health=good))
    assert any(i.priority == "critical" and i.category == "health" for i in insights)


def test_insights_never_invent_numbers() -> None:
    reg = BenchmarkRegression("hash_lookup", 45.0, 61.0, 35.6, "CRITICAL")
    insights = generate_insights(_ctx(benchmark_regressions=[reg]))
    perf = next(i for i in insights if i.category == "performance")
    assert perf.evidence["previous_ms"] == 45.0
    assert perf.evidence["current_ms"] == 61.0
    assert "45.0" in perf.message and "61.0" in perf.message
