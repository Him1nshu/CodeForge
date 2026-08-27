import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { HealthHistoryPoint, HealthScoreResponse, MetricBundle } from "../lib/types";

export function useProject(projectId: string | undefined) {
  const [health, setHealth] = useState<HealthScoreResponse | null>(null);
  const [history, setHistory] = useState<HealthHistoryPoint[]>([]);
  const [metrics, setMetrics] = useState<MetricBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const [h, hist, m] = await Promise.all([
        api.getHealth(projectId),
        api.getHealthHistory(projectId),
        api.getMetrics(projectId),
      ]);
      setHealth(h);
      setHistory(hist);
      setMetrics(m);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { health, history, metrics, error, loading, refresh };
}