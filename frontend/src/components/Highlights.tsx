import type { PlayerRow } from "../types";

function best(rows: PlayerRow[], key: (p: PlayerRow) => number) {
  let top: PlayerRow | null = null;
  for (const p of rows) if (!top || key(p) > key(top)) top = p;
  return top;
}

function Badge({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div
      style={{
        flex: "1 1 120px",
        background: "var(--panel2)",
        border: "1px solid var(--line)",
        borderRadius: 8,
        padding: "10px 12px",
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "var(--muted)",
          textTransform: "uppercase",
          letterSpacing: 0.5,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--muted)" }}>{sub}</div>}
    </div>
  );
}

export function Highlights({ rows }: { rows: PlayerRow[] }) {
  const aces = rows.filter((p) => p.k5 > 0);
  const quads = rows.filter((p) => p.k4 > 0);
  const topEntry = best(rows, (p) => p.entry_kills);
  const topClutch = best(rows, (p) => p.clutches);

  return (
    <div className="card">
      <h3>Destacados de la partida</h3>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Badge
          label="Aces (5K)"
          value={aces.length ? String(aces.length) : "–"}
          sub={aces.map((p) => p.name ?? "?").join(", ") || "ninguno"}
        />
        <Badge
          label="Cuádruples (4K)"
          value={String(quads.reduce((a, p) => a + p.k4, 0) || "–")}
          sub={quads.map((p) => p.name ?? "?").join(", ") || "ninguno"}
        />
        <Badge
          label="Mejor entry"
          value={topEntry ? `${topEntry.entry_kills} FK` : "–"}
          sub={topEntry?.name ?? ""}
        />
        <Badge
          label="Mejor clutch"
          value={topClutch ? `${topClutch.clutches} clutch` : "–"}
          sub={topClutch?.name ?? ""}
        />
      </div>
    </div>
  );
}
