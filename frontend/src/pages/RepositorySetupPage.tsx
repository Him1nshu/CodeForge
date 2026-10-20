import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

function getProjectName(repositoryUrl: string): string {
  const url = new URL(repositoryUrl);
  const repository = url.pathname.replace(/\/+$/, "").split("/").pop() ?? "";
  return repository.replace(/\.git$/, "").replace(/[-_]+/g, " ").trim();
}

function isGithubRepository(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "github.com" && url.pathname.split("/").filter(Boolean).length >= 2;
  } catch {
    return false;
  }
}

export function RepositorySetupPage() {
  const navigate = useNavigate();
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUrl = repositoryUrl.trim().replace(/\/+$/, "");

    if (!isGithubRepository(normalizedUrl)) {
      setError("Enter a valid public GitHub repository URL, such as https://github.com/acme/checkout.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      const project = await api.createProject({
        project_name: getProjectName(normalizedUrl),
        repository_url: normalizedUrl,
      });
      navigate(`/projects/${project.id}/overview`);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "We could not add that repository.");
      setSubmitting(false);
    }
  }

  return (
    <main className="relative flex min-h-full items-center justify-center overflow-hidden px-5 py-12 sm:px-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(14,165,233,0.14),transparent_44%)]" />
      <div className="relative w-full max-w-5xl">
        <header className="mb-12 flex items-center justify-between">
          <Link to="/projects" className="flex items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-sky-300">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-400 text-lg font-bold text-slate-950">C</span>
            <span>
              <span className="block text-sm font-semibold tracking-[0.2em] text-white">CODEFORGE</span>
              <span className="block text-xs text-slate-500">Engineering intelligence</span>
            </span>
          </Link>
          <Link to="/projects" className="text-sm text-slate-400 transition hover:text-white">
            View projects <span aria-hidden="true">→</span>
          </Link>
        </header>

        <div className="grid items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
          <section>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1.5 text-xs font-medium text-sky-300">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-300" />
              Start with your source
            </div>
            <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
              Build with the code you already trust.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-400">
              Connect a GitHub repository and CodeForge will turn its build history into a clear, actionable engineering picture.
            </p>

            <form onSubmit={handleSubmit} className="mt-9 max-w-xl">
              <label htmlFor="repository-url" className="mb-2 block text-sm font-medium text-slate-200">
                GitHub repository URL
              </label>
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true">
                    ↗
                  </span>
                  <input
                    id="repository-url"
                    type="url"
                    value={repositoryUrl}
                    onChange={(event) => {
                      setRepositoryUrl(event.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="https://github.com/owner/repository"
                    autoComplete="url"
                    className="h-12 w-full rounded-xl border border-bp-edge bg-bp-panel/80 pl-10 pr-4 text-sm text-white shadow-lg shadow-slate-950/20 placeholder:text-slate-600 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/20"
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="h-12 rounded-xl bg-sky-400 px-6 text-sm font-semibold text-slate-950 transition hover:bg-sky-300 disabled:cursor-wait disabled:opacity-60"
                >
                  {submitting ? "Connecting…" : "Connect repository"}
                </button>
              </div>
              {error ? <p className="mt-3 text-sm text-rose-300" role="alert">{error}</p> : null}
              <p className="mt-3 text-xs text-slate-500">Example: github.com/vercel/next.js</p>
            </form>
          </section>

          <aside className="rounded-2xl border border-bp-edge bg-bp-panel/70 p-6 shadow-2xl shadow-slate-950/30">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">What happens next</p>
            <div className="mt-6 space-y-6">
              {[
                ["01", "Connect your repository", "We create a project space from the GitHub URL you provide."],
                ["02", "Bring in build data", "Use the collector or CI workflow to send build reports."],
                ["03", "See the signal", "Explore health, trends, tests, benchmarks, and architecture in one place."],
              ].map(([number, title, description]) => (
                <div key={number} className="flex gap-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-xs font-semibold text-sky-300">{number}</span>
                  <div>
                    <h2 className="text-sm font-medium text-slate-100">{title}</h2>
                    <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-7 border-t border-bp-edge pt-5 text-xs leading-5 text-slate-500">
              Your repository URL is used to identify the project. CodeForge does not ask for your GitHub password here.
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
