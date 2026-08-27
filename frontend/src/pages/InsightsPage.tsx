import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { InsightResponse } from "../lib/types";

const PRIORITY_COLOR: Record<string, string> = {
  critical: "border-red-500/60",
  high: "border-orange-500/50",
  medium: "border-amber-500/40",
  low: "border-slate-600",
  info: "border-slate-600",
};

export function InsightsPage() {
  const { projectId } = useParams();
  const [insights, setInsights] = useState<InsightResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    void api
      .getInsights(projectId, 200)
      .then((data) => !cancelled && setInsights(data))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (error) return <p className="text-red-400">{error}</p>;
  if (!insights) return <p className="text-slate-500">Loading…</p>;
  if (insights.length === 0) return <p className="text-slate-500">No insights generated yet.</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Insights ({insights.length})</h1>
      {insights.map((ins) => (
        <div key={ins.id} className={`rounded-lg border-l-4 ${PRIORITY_COLOR[ins.priority] ?? PRIORITY_COLOR.info} border border-bp-edge bg-bp-panel p-4`}>
          <div className="flex items-center justify-between">
            <h3 className="font-medium">{ins.title}</h3>
            <span className="text-xs tabular-nums text-slate-500">
              {ins.priority} · {ins.category}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-300">{ins.message}</p>
          {ins.recommendation ? (
            <p className="mt-2 bg-sky-500/10 px-3 py-2 text-sm text-sky-300">
              <span className="font-medium">Recommendation: </span>
              {ins.recommendation}
            </p>
          ) : null}
          {Object.keys(ins.evidence ?? {}).length > 0 ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-slate-500">Evidence</summary>
              <pre className="mt-2 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-300">
                {JSON.stringify(ins.evidence, null, 2)}
              </pre>
            </details>
          ) : null}
        </div>
      ))}
    </div>
  );
}