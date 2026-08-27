import {
  type BuildHistoryRow,
  type HealthHistoryPoint,
  type HealthScoreResponse,
  type InsightResponse,
  type MetricBundle,
  type Paginated,
  type ProjectResponse,
  type TrendItem,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-json body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  listProjects: (q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<ProjectResponse[]>(`/projects${qs}`);
  },
  getProject: (id: string) => request<ProjectResponse>(`/projects/${id}`),
  getHealth: (id: string) => request<HealthScoreResponse>(`/projects/${id}/health`),
  getHealthHistory: (id: string) =>
    request<HealthHistoryPoint[]>(`/projects/${id}/health/history`),
  getMetrics: (id: string) => request<MetricBundle>(`/projects/${id}/metrics`),
  getTrends: (id: string) => request<TrendItem[]>(`/projects/${id}/trends`),
  getInsights: (id: string, limit = 100) =>
    request<InsightResponse[]>(`/projects/${id}/insights?limit=${limit}`),
  getBuildHistory: (id: string, page = 1, pageSize = 50) =>
    request<Paginated<BuildHistoryRow>>(`/projects/${id}/build-history?page=${page}&page_size=${pageSize}`),
  getArchitecture: (id: string) => request<unknown>(`/projects/${id}/architecture`),
};