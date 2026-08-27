import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { Panel, ScoreCard } from "../components/ui";

function Row({ k, v, tone }: { k: string; v: string | number; tone?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-bp-edge py-1.5 text-sm last:border-0">
      <span className="text-slate-400">{k}</span>
      <span className={`tabular-nums ${tone ?? ""}`}>{v}</span>
    </div>
  );
}

export function TestsPage() {
  const { projectId } = useParams();
  const { metrics, error, loading } = useProject(projectId);

  if (loading) return <p className="text-slate-500">Loading…</p>;
  if (error) return <p className="text-red-400">{error}</p>;
  if (!metrics) return <p className="text-slate-500">No data yet.</p>;

  const t = metrics.tests;
  if (t.missing) return <p className="text-slate-500">Tests were not collected for this build.</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <ScoreCard label="Total" value={t.total} />
        <ScoreCard label="Passed" value={t.passed} />
        <ScoreCard label="Failed" value={t.failed} />
        <ScoreCard label="Skipped" value={t.skipped} />
        <ScoreCard label="Pass rate" value={t.total ? Math.round(t.pass_rate * 100) / 100 : 0} />
        <ScoreCard label="Execution" value={t.execution_time_ms} suffix="ms" />
      </div>

      {t.failures && t.failures.length > 0 ? (
        <Panel title={`Failure details (${t.failures.length})`}>
          <div className="flex flex-col gap-3">
            {t.failures.map((f) => (
              <div key={f.name} className="rounded border border-red-500/40 bg-red-500/5 p-3">
                <div className="font-mono text-sm text-red-300">{f.name}</div>
                {f.message ? (
                  <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-red-200/80">{f.message}</pre>
                ) : (
                  <div className="mt-1 text-xs text-red-200/60">no failure message recorded</div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      {t.flaky_tests.length > 0 ? (
        <Panel title="Flaky tests">
          <ul className="flex flex-col gap-1 font-mono text-xs">
            {t.flaky_tests.map((name) => (
              <li key={name} className="text-amber-400">
                {name}
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Panel title="Per-test stability">
        {t.stability?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2">Test</th>
                <th className="py-2">Status</th>
                <th className="py-2">Executions</th>
                <th className="py-2">Passes</th>
                <th className="py-2">Failures</th>
                <th className="py-2">Flaky score</th>
              </tr>
            </thead>
            <tbody>
              {t.stability.map((s) => (
                <tr key={s.name} className="border-t border-bp-edge">
                  <td className="py-2 font-mono text-xs">{s.name}</td>
                  <td className="py-2">{s.status}</td>
                  <td className="py-2 tabular-nums">{s.executions}</td>
                  <td className="py-2 tabular-nums">{s.passes}</td>
                  <td className="py-2 tabular-nums text-red-400">{s.failures}</td>
                  <td className="py-2 tabular-nums">{s.flaky_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-slate-500">No per-test data.</p>
        )}
        <div className="mt-2 flex flex-col">
          <Row k="Pass rate" v={`${(t.pass_rate * 100).toFixed(1)}%`} tone="text-emerald-400" />
        </div>
      </Panel>
    </div>
  );
}