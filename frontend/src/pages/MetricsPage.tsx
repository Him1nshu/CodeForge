import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { Panel, ScoreCard } from "../components/ui";

function Row({ k, v }: { k: string; v: string | number | null | undefined }) {
  return (
    <div className="flex items-center justify-between border-b border-bp-edge py-1.5 text-sm last:border-0">
      <span className="text-slate-400">{k}</span>
      <span className="tabular-nums">{v === null || v === undefined ? "—" : v}</span>
    </div>
  );
}

export function MetricsPage() {
  const { projectId } = useParams();
  const { metrics, error, loading } = useProject(projectId);

  if (loading) return <p className="text-slate-500">Loading…</p>;
  if (error) return <p className="text-red-400">{error}</p>;
  if (!metrics) return <p className="text-slate-500">No data yet.</p>;

  const cm = metrics.code_metrics;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <ScoreCard label="Binary size" value={metrics.metrics.binary_size} suffix=" B" />
        <ScoreCard label="Artifacts" value={metrics.metrics.artifact_count} />
        <ScoreCard label="Lines of code" value={cm?.lines_of_code} />
        <ScoreCard label="Functions" value={cm?.functions} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Code quality">
          <div className="flex flex-col">
            <Row k="Total cyclomatic complexity" v={cm?.cyclomatic_complexity_total} />
            <Row k="Avg function complexity" v={cm?.avg_function_complexity?.toFixed(1)} />
            <Row k="Max function complexity" v={cm?.max_function_complexity} />
            <Row k="Functions above threshold" v={cm?.functions_above_threshold} />
            <Row k="Complexity threshold" v={cm?.complexity_threshold} />
            <Row k="Maintainability index" v={cm?.maintainability_index?.toFixed(1)} />
            <Row k="Avg function length (lines)" v={cm?.avg_function_length?.toFixed(1)} />
          </div>
        </Panel>
        <Panel title="Complexity hotspots">
          {cm?.top_complex_functions?.length ? (
            <ul className="flex flex-col gap-2 text-sm">
              {cm.top_complex_functions.map((f, i) => (
                <li key={i} className="flex items-center justify-between gap-4">
                  <span className="truncate font-mono text-xs">
                    {f.file}:{f.function}
                  </span>
                  <span className="tabular-nums text-amber-400">{f.complexity}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No complexity data.</p>
          )}
        </Panel>
      </div>

      <Panel title="Build">
        <div className="flex flex-col">
          <Row k="Status" v={metrics.build.status} />
          <Row k="Duration" v={metrics.build.duration_ms ? `${metrics.build.duration_ms} ms` : null} />
          <Row k="Warnings" v={metrics.build.compiler_warnings} />
          <Row k="Errors" v={metrics.build.compiler_errors} />
          <Row k="Dependencies" v={metrics.dependencies.count} />
        </div>
      </Panel>
    </div>
  );
}