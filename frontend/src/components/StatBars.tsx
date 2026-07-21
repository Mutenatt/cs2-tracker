import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PlayerRow } from "../types";

const ACCENT = "#f5a623";

interface Props {
  title: string;
  rows: PlayerRow[];
  metric: "adr" | "kd";
  color: string;
}

export function StatBars({ title, rows, metric, color }: Props) {
  const data = [...rows]
    .map((p) => ({ name: p.name ?? "?", value: p[metric] }))
    .sort((a, b) => a.value - b.value);

  return (
    <div className="card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 16 }}>
          <XAxis
            type="number"
            tick={{ fill: "#8b90a0", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fill: "#e7e9ee", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "#ffffff10" }}
            contentStyle={{
              background: "#1f222b",
              border: "1px solid #2a2e3a",
              borderRadius: 8,
              color: "#e7e9ee",
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={i === data.length - 1 ? ACCENT : color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
