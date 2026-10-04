import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { ProjectResponse } from "../lib/types";
import { gradeColor, PageMessage } from "../components/ui";

export function ProjectsListPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void api
      .listProjects(q || undefined)
      .then((data) => {
        if (!cancelled) {
          setProjects(data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [q, refreshToken]);

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="project-search" className="sr-only">Search projects</label>
          <input
            id="project-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search projects"
            className="w-44 rounded-lg border border-bp-edge bg-slate-800 px-3 py-1.5 text-sm placeholder:text-slate-500 focus-visible:outline-2 focus-visible:outline-sky-300 sm:w-56"
          />
          {q ? (
            <button
              type="button"
              onClick={() => setQ("")}
              className="rounded px-2 py-1 text-sm text-slate-400 hover:bg-slate-800 hover:text-white"
              aria-label="Clear project search"
            >
              Clear
            </button>
          ) : null}
        </div>
      </div>
      {loading ? <PageMessage>Loading projects…</PageMessage> : null}
      {error ? <PageMessage error onRetry={() => setRefreshToken((value) => value + 1)}>{error}</PageMessage> : null}
      {!loading && projects.length === 0 && !error ? (
        <div className="rounded-lg border border-dashed border-bp-edge bg-bp-panel/60 p-8 text-center">
          <h2 className="text-lg font-medium text-slate-200">No projects yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
            Create a project through the API, then upload a collector report to populate the dashboard.
          </p>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="mt-5 inline-flex rounded-md bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
          >
            Open API docs
          </a>
        </div>
      ) : null}
      <div className="flex flex-col gap-3">
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/projects/${p.id}/overview`}
            className="rounded-lg border border-bp-edge bg-bp-panel p-4 transition hover:border-sky-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
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