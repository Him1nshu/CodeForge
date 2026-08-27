import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { TrendItem } from "../lib/types";

function color(direction: string, significance: string): string {
  if (significance === "critical" || direction === "degrading") return "#ef4444";
  if (significance === "warning") return "#f59e0b";
  if (direction === "improving") return "#22c55e";
  return "#94a3b8";
}

export function TrendsPage() {
  const { projectId } = useParams();
  const [trends, setTrends] = useState<TrendItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    void api
      .getTrends(projectId)
      .then((data) => !cancelled && setTrends(data))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (error) return <p className="text-red-400">{error}</p>;
  if (!trends) return <p className="text-slate-500">Loading…</p>;
  if (trends.length === 0) return <p className="text-slate-500">No trends detected yet.</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="mb-4 text-2xl font-semibold">Metric trends</h1>
      <div className="flex flex-col gap-3">
        {trends.map((t) => {
          const change = t.change_percent ?? 0;
          const arrow = change > 0 ? "▲" : change < 0 ? "▼" : "•";
          return (
            <div key={`${t.metric}-${t.build_number}`} className="rounded-lg border border-bp-edge bg-bp-panel p-4">
              <div className="flex items-center justify-between">
                <div className="font-medium capitalize">{t.metric.replace(/_/g, " ")}</div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-slate-400">
                    build {t.build_number}
                  </span>
                  <span className="tabular-nums text-slate-300">
                    {t.current_value == null ? "—" : Number(t.current_value.toFixed(2))}
                    {t.previous_value != null ? ` ← ${Number(t.previous_value.toFixed(2))}` : ""}
                  </span>
                  <span className="w-32 text-right tabular-nums" style={{ color: color(t.direction, t.significance) }}>
                    {t.change_percent != null ? `${arrow} ${Math.abs(change).toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>
              <div className="mt-1 text-xs">
                <span className="text-slate-500">direction: {t.direction}</span>
                <span className="mx-2 text-slate-600">·</span>
                <span className="text-slate-500">significance: {t.significance}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}