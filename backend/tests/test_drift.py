"""Unit tests for the pure architecture drift engine."""

from app.intelligence.drift import Edge, compute_drift, drift_severity

MAPPING = {
    "presentation": "presentation",
    "application": "application",
    "domain": "domain",
    "infrastructure": "infrastructure",
}


def test_clean_layered_graph() -> None:
    result = compute_drift(
        [
            Edge("presentation", "application"),
            Edge("application", "domain"),
            Edge("domain", "infrastructure"),
        ],
        MAPPING,
    )
    assert result.drift_score == 0.0
    assert result.layer_violations == 0
    assert result.cyclic_dependencies == 0
    assert result.module_count == 4
    assert result.edge_count == 3
    assert drift_severity(result.drift_score) == "LOW"


def test_domain_to_presentation_is_a_violation() -> None:
    result = compute_drift(
        [
            Edge("presentation", "application"),
            Edge("domain", "presentation"),  # violation: must not depend upward
        ],
        MAPPING,
    )
    assert result.layer_violations == 1
    assert result.drift_score > 0
    assert any(v.violation_type == "layer" for v in result.violations)


def test_cycle_detection() -> None:
    result = compute_drift(
        [Edge("a", "b"), Edge("b", "c"), Edge("c", "a")],
        {},
    )
    assert result.cyclic_dependencies >= 3


def test_jump_coupling_counts() -> None:
    result = compute_drift(
        [Edge("presentation", "infrastructure")],
        MAPPING,
    )
    assert result.unexpected_coupling >= 1
    assert result.layer_violations >= 1  # also a layer violation


def test_severity_buckets() -> None:
    assert drift_severity(0) == "LOW"
    assert drift_severity(20) == "MEDIUM"
    assert drift_severity(45) == "HIGH"
    assert drift_severity(99) == "HIGH"


def test_graph_shape() -> None:
    result = compute_drift([Edge("a", "b")], {})
    assert result.graph["nodes"]
    assert result.graph["edges"][0]["source"] == "a"
    assert result.graph["edges"][0]["target"] == "b"
