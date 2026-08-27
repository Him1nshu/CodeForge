import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Panel, ScoreCard } from "../components/ui";

interface ArchitectureData {
  drift_score: number | null;
  layer_violations: number;
  unexpected_coupling: number;
  module_count: number;
  cyclic_dependencies: number;
  direction_violations: number;
  edge_count: number;
  dependency_graph?: { nodes: string[]; edges: { source: string; target: string }[] };
}

export function ArchitecturePage() {
  const { projectId } = useParams();
  const [data, setData] = useState<ArchitectureData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    void api
      .getArchitecture(projectId)
      .then((d) => !cancelled && setData(d as ArchitectureData))
      .catch(() => !cancelled && setError("no architecture analysis"));
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (error) return <p className="text-slate-500">{error} for this project yet.</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Architecture</h1>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <ScoreCard label="Drift score" value={data.drift_score} />
        <ScoreCard label="Modules" value={data.module_count} />
        <ScoreCard label="Edges" value={data.edge_count} />
        <ScoreCard label="Layer violations" value={data.layer_violations} />
        <ScoreCard label="Direction violations" value={data.direction_violations} />
        <ScoreCard label="Cyclic deps" value={data.cyclic_dependencies} />
        <ScoreCard label="Unexpected coupling" value={data.unexpected_coupling} />
      </div>
      {data.dependency_graph?.edges?.length ? (
        <Panel title={`Dependency graph (${data.dependency_graph.nodes.length} modules)`}>
          <div className="grid grid-cols-2 gap-1 md:grid-cols-3">
            {data.dependency_graph.edges.map((e, i) => (
              <div key={i} className="font-mono text-xs text-slate-300">
                <span className="text-slate-500">{e.source}</span> → <span>{e.target}</span>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}