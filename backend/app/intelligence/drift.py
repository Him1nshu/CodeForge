"""Pure drift detection over a C++ include module graph.

Inputs: list of directed module edges (source depends on target via #include)
and a module→layer mapping. Outputs a drift score (0–100), violation counts,
graph nodes/edges for visualization, and specific violation records.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Intended dependency layering: inner depends on outer is a violation.
# presentation -> application -> domain -> infrastructure
DEFAULT_LAYER_ORDER = ["presentation", "application", "domain", "infrastructure"]
DEFAULT_LAYER_INDEX = {layer: i for i, layer in enumerate(DEFAULT_LAYER_ORDER)}


@dataclass
class Edge:
    source: str
    target: str


@dataclass
class Violation:
    violation_type: str
    source_module: str
    target_module: str
    source_layer: str | None
    target_layer: str | None
    message: str


@dataclass
class DriftResult:
    drift_score: float
    layer_violations: int
    unexpected_coupling: int
    direction_violations: int
    cyclic_dependencies: int
    module_count: int
    edge_count: int
    graph: dict
    violations: list[Violation] = field(default_factory=list)


def _detect_cycles(edges: list[Edge]) -> set[str]:
    """Return the set of modules involved in at least one directed cycle."""
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.source, []).append(e.target)
    visited: set[str] = set()
    stack: list[str] = []
    in_stack: set[str] = set()
    cyclic: set[str] = set()

    def dfs(u: str) -> None:
        visited.add(u)
        stack.append(u)
        in_stack.add(u)
        for v in adj.get(u, []):
            if v in in_stack:
                cyclic.update(stack[stack.index(v):])
            elif v not in visited:
                dfs(v)
        stack.pop()
        in_stack.discard(u)

    for u in list(adj):
        if u not in visited:
            dfs(u)
    return cyclic


def _layer_of(module: str, mapping: dict[str, str]) -> str | None:
    layer = mapping.get(module)
    if layer:
        return layer.lower()
    # Best-effort: infer from a leading path component.
    first = module.split("/")[0].lower()
    return mapping.get(first) or first.lower() if first in DEFAULT_LAYER_INDEX else None


def compute_drift(
    edges: list[Edge],
    layer_mapping: dict[str, str] | None = None,
    layer_order: list[str] | None = None,
) -> DriftResult:
    """Compute drift indicators and a normalized 0–100 score.

    Score components (scaled so typical clean projects score ~0):
      layer_violations     4 pts each
      unexpected_coupling  3 pts each (edges jumping >1 layer)
      direction_violations 3 pts per offending module
      cycles               6 pts per module involved in a cycle
    """
    mapping = dict(layer_mapping or {})
    order = DEFAULT_LAYER_ORDER if layer_order is None else layer_order
    index = {layer.strip().lower(): i for i, layer in enumerate(order)}

    layer_violations: list[Violation] = []
    coupling_jumps = 0
    offending_modules: set[str] = set()

    for e in edges:
        sl = _layer_of(e.source, mapping)
        tl = _layer_of(e.target, mapping)
        sidx = index.get(sl or "")
        tidx = index.get(tl or "")
        if sidx is not None and tidx is not None:
            distance = abs(sidx - tidx)
            # A dependency is a layering violation when it goes backwards in the
            # layer order OR skips intermediate layers (jump coupling).
            if distance > 1:
                coupling_jumps += 1
            if tidx < sidx or distance > 1:
                layer_violations.append(
                    Violation(
                        violation_type="layer",
                        source_module=e.source,
                        target_module=e.target,
                        source_layer=sl,
                        target_layer=tl,
                        message=f"{sl} must not depend on {tl} ({e.source} includes {e.target})",
                    )
                )
                offending_modules.add(e.source)

    cyclic = _detect_cycles(edges)
    cyclic_violations = [
        Violation(
            violation_type="cycle",
            source_module=m,
            target_module=m,
            source_layer=_layer_of(m, mapping),
            target_layer=_layer_of(m, mapping),
            message=f"module '{m}' participates in a dependency cycle",
        )
        for m in sorted(cyclic)
    ]

    drift_score = round(
        min(
            100.0,
            len(layer_violations) * 4.0
            + coupling_jumps * 3.0
            + len(offending_modules) * 3.0
            + len(cyclic) * 6.0,
        ),
        1,
    )

    modules = sorted({e.source for e in edges} | {e.target for e in edges})
    nodes = [{"id": m, "label": m, "layer": _layer_of(m, mapping) or "unmapped"} for m in modules]
    violated_edges = {(v.source_module, v.target_module) for v in layer_violations}
    graph_edges = [
        {
            "source": e.source,
            "target": e.target,
            "kind": "violation" if (e.source, e.target) in violated_edges else "allowed",
        }
        for e in edges
    ]

    return DriftResult(
        drift_score=drift_score,
        layer_violations=len(layer_violations),
        unexpected_coupling=coupling_jumps,
        direction_violations=len(offending_modules),
        cyclic_dependencies=len(cyclic),
        module_count=len(modules),
        edge_count=len(edges),
        graph={"nodes": nodes, "edges": graph_edges},
        violations=layer_violations + cyclic_violations,
    )


def drift_severity(score: float) -> str:
    if score < 15:
        return "LOW"
    if score < 40:
        return "MEDIUM"
    return "HIGH"
