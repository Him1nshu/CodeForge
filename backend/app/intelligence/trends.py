"""Pure trend / anomaly detection engine.

Given a time series of a numeric metric it computes direction
(IMPROVING/STABLE/DEGRADING/CRITICAL), percentage change vs previous build,
moving average, and a Z-score anomaly flag. Direction semantics depend on
whether a higher metric value is better or worse.
"""

import statistics
from dataclasses import dataclass

# Per-metric directional semantics (assemble series in build order).
LOWER_IS_BETTER = {
    "build_duration_ms": True,
    "compiler_warnings": True,
    "compiler_errors": True,
    "binary_size_bytes": True,
    "static_analysis_issues": True,
    "max_function_complexity": True,
    "avg_function_complexity": True,
    "functions_above_threshold": True,
    "mean_test_duration_ms": True,
    "mean_benchmark_ms": True,
    "architecture_drift_score": True,
    "dependency_churn": True,
}
HIGHER_IS_BETTER = {
    "test_pass_rate": False,
    "maintainability_index": False,
    "test_count": False,
}
DIRECTION_FOR_METRIC = {**LOWER_IS_BETTER, **HIGHER_IS_BETTER}


@dataclass
class TrendResult:
    metric: str
    current: float | None
    previous: float | None
    change_percent: float | None
    moving_avg: float | None
    direction: str
    anomaly: bool = False


def _anomaly(series: list[float], current: float) -> bool:
    if len(series) < 4:
        return False
    history = series[:-1]
    try:
        mean = statistics.fmean(history)
        stdev = statistics.stdev(history)
    except statistics.StatisticsError:
        return False
    if stdev == 0:
        return False
    return abs((current - mean) / stdev) > 2.5


def classify_trend(metric: str, series: list[float], window: int = 4) -> TrendResult:
    """Classify the full series; direction uses the last two points."""
    lower_is_better = DIRECTION_FOR_METRIC.get(metric, True)
    if not series:
        return TrendResult(metric=metric, current=None, previous=None, change_percent=None, moving_avg=None, direction="STABLE", anomaly=False)

    current = series[-1]
    previous = series[-2] if len(series) >= 2 else None
    ma = statistics.fmean(series[-window:]) if series else None

    change_percent = None
    if previous and previous != 0:
        change_percent = (current - previous) / abs(previous) * 100.0

    direction = "STABLE"
    if change_percent is not None:
        upward = change_percent > 0
        if lower_is_better:
            if upward and change_percent >= 25:
                direction = "CRITICAL"
            elif upward and change_percent >= 10:
                direction = "DEGRADING"
            elif not upward and change_percent <= -5:
                direction = "IMPROVING"
        else:
            if upward and change_percent >= 3:
                direction = "IMPROVING"
            elif not upward and change_percent <= -10:
                direction = "CRITICAL"
            elif not upward and change_percent <= -5:
                direction = "DEGRADING"

    return TrendResult(
        metric=metric,
        current=round(current, 4),
        previous=round(previous, 4) if previous is not None else None,
        change_percent=round(change_percent, 2) if change_percent is not None else None,
        moving_avg=round(ma, 4) if ma is not None else None,
        direction=direction,
        anomaly=_anomaly(series, current),
    )


@dataclass
class BenchmarkRegression:
    name: str
    previous_ms: float
    current_ms: float
    change_percent: float
    severity: str  # OK / WARNING / CRITICAL


WARN_REGRESSION_PCT = 10.0
CRITICAL_REGRESSION_PCT = 25.0


def classify_benchmark_regression(name: str, previous_ms: float | None, current_ms: float | None) -> BenchmarkRegression | None:
    """Regression models: a rise in mean time is bad. Thresholds configurable."""
    if not previous_ms or not current_ms or previous_ms <= 0:
        return None
    change = (current_ms - previous_ms) / previous_ms * 100.0
    if change <= 0 or change <= WARN_REGRESSION_PCT:
        severity = "OK"
    elif change <= CRITICAL_REGRESSION_PCT:
        severity = "WARNING"
    else:
        severity = "CRITICAL"
    return BenchmarkRegression(
        name=name,
        previous_ms=round(previous_ms, 3),
        current_ms=round(current_ms, 3),
        change_percent=round(change, 1),
        severity=severity,
    )
