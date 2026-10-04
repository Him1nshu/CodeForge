import { useState } from "react";
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
  const [menuOpen, setMenuOpen] = useState(false);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `block rounded px-3 py-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300 ${
      isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
    }`;

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <a
        href="#main-content"
        className="absolute left-4 top-2 z-50 -translate-y-16 rounded-md bg-sky-400 px-3 py-2 text-sm font-medium text-slate-950 transition-transform focus:translate-y-0"
      >
        Skip to main content
      </a>
      <header className="flex items-center justify-between border-b border-bp-edge bg-bp-panel p-4 md:hidden">
        <div>
          <div className="text-lg font-semibold tracking-tight">CODEFORGE</div>
          <div className="text-xs text-slate-400">Engineering Intelligence</div>
        </div>
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="project-navigation"
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded-md border border-bp-edge px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-sky-300"
        >
          {menuOpen ? "Close menu" : "Menu"}
        </button>
      </header>
      <aside
        id="project-navigation"
        className={`${menuOpen ? "block" : "hidden"} border-b border-bp-edge bg-bp-panel p-4 md:block md:w-60 md:shrink-0 md:border-b-0 md:border-r`}
      >
        <div className="mb-6">
          <div className="text-xl font-semibold tracking-tight">CODEFORGE</div>
          <div className="text-xs text-slate-400">Engineering Intelligence</div>
        </div>
        <nav aria-label="Project navigation" className="flex flex-col gap-1 text-sm">
          <NavLink
            to="/projects"
            end
            className={linkClass}
            onClick={() => setMenuOpen(false)}
          >
            Projects
          </NavLink>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={`${base}/${item.to}`}
              className={linkClass}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 overflow-y-auto p-4 outline-none sm:p-6">
        <Outlet />
      </main>
    </div>
  );
}