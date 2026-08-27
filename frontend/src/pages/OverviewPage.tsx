import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { HealthTrendChart } from "../components/HealthTrendChart";
import { gradeColor, Panel, ScoreCard, StatusBadge } from "../components/ui";

export function OverviewPage() {
  const { projectId } = useParams();
  const { health, history, metrics, error, loading } = useProject(projectId);

  if (loading) return <p className="text-slate-500">Loading…</p>;
  if (error) return <p className="text-red-400">{error}</p>;
  if (!health || !metrics) return <p className="text-slate-500">No data for this project yet.</p>;

  const build = metrics.build;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-6">
        <div>
          <div className="text-4xl font-bold tabular-nums" style={{ color: gradeColor(health.grade) }}>
            {health.overall_score.toFixed(1)}
          </div>
          <div className="text-sm text-slate-400">{health.grade} · formula {health.formula_version}</div>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
          {Object.entries(health.categories).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-4">
              <span className="capitalize text-slate-400">{k.replace("_", " ")}</span>
              <span className="tabular-nums" style={{ color: gradeColor(v >= 75 ? (v >= 90 ? "GOOD" : "GOOD") : v >= 60 ? "MODERATE" : "WEAK") }}>
                {v.toFixed(0)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <ScoreCard label="Build status" value={null} hint={build.status} />
        <ScoreCard label="Warnings" value={build.compiler_warnings} />
        <ScoreCard label="Errors" value={build.compiler_errors} />
        <ScoreCard label="Duration" value={build.duration_ms ? Math.round(build.duration_ms) : undefined} suffix="ms" />
      </div>

      <Panel title="Health trend">
        <HealthTrendChart history={history} />
      </Panel>

      <Panel title="Latest build">
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <span className="text-slate-500">Build # </span>
            <span className="tabular-nums">{build.build_number}</span>
          </div>
          <div>
            <span className="text-slate-500">Status </span>
            <StatusBadge status={build.status} />
          </div>
          {build.branch ? (
            <div>
              <span className="text-slate-500">Branch </span>
              <span>{build.branch}</span>
            </div>
          ) : null}
          {build.commit_hash ? (
            <div className="font-mono text-xs">
              <span className="text-slate-500">Commit </span>
              {build.commit_hash.slice(0, 12)}
            </div>
          ) : null}
        </div>
        {metrics.tests && !metrics.tests.missing ? (
          <p className="mt-2 text-sm text-slate-400">
            {metrics.tests.passed}/{metrics.tests.total} tests passed
          </p>
        ) : null}
      </Panel>
    </div>
  );
}