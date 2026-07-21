import type { MatchesPerDayEntry } from "../../types";

export function MatchesPerDayChart({ data }: { data: MatchesPerDayEntry[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="monthly-day-chart">
      {data.map((d) => {
        const pct = d.count === 0 ? 6 : Math.round((d.count / max) * 100);
        const intensity = d.count === 0 ? 0 : 35 + Math.round((d.count / max) * 65);
        return (
          <div className="monthly-day-col" key={d.day}>
            <div
              className={`monthly-day-bar${d.count === 0 ? " zero" : ""}`}
              style={
                d.count === 0
                  ? { height: `${pct}%` }
                  : {
                      height: `${pct}%`,
                      background: `color-mix(in srgb, var(--accent-cyan) ${intensity}%, var(--bg-surface-2))`,
                    }
              }
            />
            <span className="monthly-day-label">{Number(d.day)}</span>
          </div>
        );
      })}
    </div>
  );
}
