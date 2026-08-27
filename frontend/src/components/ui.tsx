export function gradeColor(grade?: string | null): string {
  switch (grade?.toUpperCase()) {
    case "EXCELLENT":
    case "GOOD":
      return "#22c55e";
    case "MODERATE":
      return "#f59e0b";
    case "WEAK":
      return "#ef4444";
    case "CRITICAL":
      return "#dc2626";
    default:
      return "#64748b";
  }
}

export function StatusBadge({ status }: { status: string }) {
  const palette: Record<string, string> = {
    success: "bg-emerald-500/15 text-emerald-400",
    failed: "bg-red-500/15 text-red-400",
    warning: "bg-amber-500/15 text-amber-400",
    unknown: "bg-slate-500/15 text-slate-400",
  };
  const cls = palette[status.toLowerCase()] ?? palette.unknown;
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${cls}`}>{status}</span>
  );
}

export function ScoreCard({
  label,
  value,
  suffix = "",
  hint,
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-bp-edge bg-bp-panel p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">
        {value === null || value === undefined ? "—" : `${value}${suffix}`}
      </div>
      {hint ? <div className="mt-1 text-xs text-slate-400">{hint}</div> : null}
    </div>
  );
}

export function Panel({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-bp-edge bg-bp-panel p-4">
      {title ? <h3 className="mb-3 text-sm font-medium text-slate-200">{title}</h3> : null}
      {children}
    </section>
  );
}