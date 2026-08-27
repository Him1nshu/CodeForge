import { NavLink, Outlet, useParams } from "react-router-dom";

const NAV = [
  { to: "overview", label: "Overview" },
  { to: "metrics", label: "Metrics" },
  { to: "trends", label: "Trends" },
  { to: "tests", label: "Tests" },
  { to: "benchmarks", label: "Benchmarks" },
  { to: "insights", label: "Insights" },
  { to: "architecture", label: "Architecture" },
];

export function Layout() {
  const { projectId = "" } = useParams();
  const base = `/projects/${projectId}`;

  return (
    <div className="flex h-full">
      <aside className="w-60 shrink-0 border-r border-bp-edge bg-bp-panel p-4">
        <div className="mb-6">
          <div className="text-xl font-semibold tracking-tight">BuildPulse</div>
          <div className="text-xs text-slate-400">Engineering Intelligence</div>
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          <NavLink
            to="/projects"
            end
            className={({ isActive }) =>
              `rounded px-3 py-2 ${isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"}`
            }
          >
            Projects
          </NavLink>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={`${base}/${item.to}`}
              className={({ isActive }) =>
                `rounded px-3 py-2 ${isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}