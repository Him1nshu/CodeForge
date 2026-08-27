"""Unit tests for the pure trend/anomaly engine."""

import pytest

from app.intelligence.trends import (
    classify_benchmark_regression,
    classify_trend,
)


def test_stable_series() -> None:
    t = classify_trend("build_duration_ms", [100, 102, 101, 100])
    assert t.direction == "STABLE"


def test_growth_marked_degrading_for_lower_is_better() -> None:
    t = classify_trend("build_duration_ms", [100, 100, 105, 130])
    assert t.direction == "DEGRADING"
    assert t.change_percent == pytest.approx(23.8, abs=0.2)  # (130-105)/105


def test_sharp_growth_marked_critical() -> None:
    t = classify_trend("build_duration_ms", [100, 100, 100, 140])
    assert t.direction == "CRITICAL"


def test_improving_for_falls() -> None:
    t = classify_trend("build_duration_ms", [140, 120, 100, 90])
    assert t.direction == "IMPROVING"


def test_higher_is_better_semantics() -> None:
    t = classify_trend("test_pass_rate", [0.9, 0.92, 0.95, 0.98])
    assert t.direction == "IMPROVING"
    t2 = classify_trend("test_pass_rate", [0.98, 0.95, 0.9, 0.8])
    assert t2.direction == "CRITICAL"


def test_moving_average() -> None:
    t = classify_trend("x", [10, 20, 30, 40])
    assert t.moving_avg == pytest.approx(25, abs=1e-6)


def test_anomaly_flag_on_large_z() -> None:
    t = classify_trend("build_duration_ms", [100, 101, 100, 102, 100, 150])
    assert t.anomaly is True


def test_anomaly_requires_enough_history() -> None:
    t = classify_trend("build_duration_ms", [100, 100, 200])
    assert t.anomaly is False


def test_single_point() -> None:
    t = classify_trend("build_duration_ms", [100])
    assert t.direction == "STABLE"
    assert t.change_percent is None


def test_benchmark_regression_levels() -> None:
    assert classify_benchmark_regression("b", 120, 125).severity == "OK"
    w = classify_benchmark_regression("b", 120, 150)
    assert w.severity == "WARNING"
    c = classify_benchmark_regression("b", 120, 165)
    assert c.severity == "CRITICAL"
    assert c.change_percent == pytest.approx(37.5, abs=0.1)


def test_benchmark_improvement_is_ok() -> None:
    r = classify_benchmark_regression("b", 165, 120)
    assert r is not None
    assert r.severity == "OK"
