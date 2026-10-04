import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HealthHistoryPoint } from "../lib/types";

export function HealthTrendChart({ history }: { history: HealthHistoryPoint[] }) {
  if (history.length === 0) {
    return <p className="text-sm text-slate-500">No health history yet.</p>;
  }
  return (
    <figure
      role="img"
      aria-label={`Health score trend across ${history.length} builds, from build ${history[0].build_number} to build ${history[history.length - 1].build_number}`}
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={history} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
        <XAxis
          dataKey="build_number"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          label={{ value: "Build", position: "insideBottom", fill: "#64748b", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
        />
        <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          labelStyle={{ color: "#94a3b8" }}
          labelFormatter={(b) => `Build ${b}`}
        />
        <Line
          type="monotone"
          dataKey="overall_score"
          name="Health"
          stroke="#38bdf8"
          strokeWidth={2}
          dot={{ r: 3, fill: "#38bdf8" }}
        />
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">
        Health scores by build: {history.map((point) => `build ${point.build_number}: ${point.overall_score.toFixed(1)}`).join(", ")}.
      </figcaption>
    </figure>
  );
}