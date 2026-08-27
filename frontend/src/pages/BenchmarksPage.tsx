import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { Panel } from "../components/ui";

export function BenchmarksPage() {
  const { projectId } = useParams();
  const { metrics, error, loading } = useProject(projectId);

  if (loading) return <p className="text-slate-500">Loading…</p>;
  if (error) return <p className="text-red-400">{error}</p>;
  if (!metrics) return <p className="text-slate-500">No data yet.</p>;

  const benches = metrics.benchmarks;
  if (benches.length === 0) return <p className="text-slate-500">No benchmarks collected.</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Benchmarks</h1>
      {benches.map((b) => {
        const tone =
          b.status === "critical" ? "text-red-400" : b.status === "warning" ? "text-amber-400" : "text-emerald-400";
        return (
          <Panel key={b.name} title={b.name}>
            <div className="mb-2 flex items-center gap-6 text-sm">
              <span className="tabular-nums">
                latest: {b.current_mean_ms != null ? `${(b.current_mean_ms / 1000).toFixed(2)} s` : "—"}
              </span>
              {b.change_percent != null ? (
                <span className={`tabular-nums ${tone}`}>
                  Δ {b.change_percent > 0 ? "+" : ""}
                  {b.change_percent.toFixed(1)}%
                  <span className="ml-1 text-xs text-slate-500">({b.status})</span>
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-1">
              {b.points.map((p) => (
                <span key={p.build_number} title={`build ${p.build_number}`} className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-300">
                  #{p.build_number} {p.mean_ms != null ? `${(p.mean_ms / 1000).toFixed(2)}s` : "—"}
                </span>
              ))}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}