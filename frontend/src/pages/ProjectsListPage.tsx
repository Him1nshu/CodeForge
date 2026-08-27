import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { ProjectResponse } from "../lib/types";
import { gradeColor } from "../components/ui";

export function ProjectsListPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api
      .listProjects(q || undefined)
      .then((data) => {
        if (!cancelled) setProjects(data);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [q]);

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search…"
          className="rounded-lg border border-bp-edge bg-slate-800 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
        />
      </div>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      {projects.length === 0 && !error ? <p className="text-sm text-slate-500">No projects found.</p> : null}
      <div className="flex flex-col gap-3">
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/projects/${p.id}/overview`}
            className="rounded-lg border border-bp-edge bg-bp-panel p-4 transition hover:border-slate-500"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{p.project_name}</div>
                {p.description ? <div className="text-sm text-slate-400">{p.description}</div> : null}
                <div className="mt-1 text-xs text-slate-500">
                  {p.build_count ?? 0} builds
                  {p.last_build_number ? ` · latest build #${p.last_build_number}` : ""}
                </div>
              </div>
              {p.last_health_score !== null && p.last_health_score !== undefined ? (
                <div className="text-right">
                  <div className="text-2xl font-semibold tabular-nums" style={{ color: gradeColor(p.last_grade) }}>
                    {p.last_health_score.toFixed(1)}
                  </div>
                  <div className="text-xs text-slate-400">{p.last_grade}</div>
                </div>
              ) : null}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}