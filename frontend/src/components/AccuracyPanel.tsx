import type { AccuracyStats } from "../types";
import { AccuracySilhouette } from "./AccuracySilhouette";

const SPARK_W = 300;
const SPARK_H = 80;
const SPARK_PAD = 10;

interface Zone {
  key: "head" | "body" | "legs";
  label: string;
  pct: number;
  hits: number;
}

// Mayor % -> verde (--go), segunda -> cian (--recon), menor -> sin color
// (var(--text)) -- calculado dinámicamente, no una zona fija por nombre.
function zoneColors(zones: Zone[]): Record<string, string> {
  const ranked = [...zones].sort((a, b) => b.pct - a.pct);
  const colors: Record<string, string> = {};
  ranked.forEach((z, i) => {
    colors[z.key] = i === 0 ? "var(--go)" : i === 1 ? "var(--recon)" : "var(--text)";
  });
  return colors;
}

function Sparkline({ series }: { series: number[] }) {
  if (series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min;
  const x = (i: number) => SPARK_PAD + (i / (series.length - 1)) * (SPARK_W - 2 * SPARK_PAD);
  const y = (v: number) =>
    span === 0 ? SPARK_H / 2 : SPARK_PAD + ((max - v) / span) * (SPARK_H - 2 * SPARK_PAD);
  const d = series
    .map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} style={{ width: "100%", display: "block" }}>
      <line x1={0} y1={18} x2={SPARK_W} y2={18} stroke="var(--line)" strokeWidth={1} />
      <line x1={0} y1={42} x2={SPARK_W} y2={42} stroke="var(--line)" strokeWidth={1} />
      <line x1={0} y1={66} x2={SPARK_W} y2={66} stroke="var(--line)" strokeWidth={1} />
      <path d={d} fill="none" stroke="#ff5454" strokeWidth={2.5} />
      <text x={SPARK_W - 2} y={22} fill="var(--text-faint)" fontSize={9} textAnchor="end">
        {max.toFixed(0)}%
      </text>
      <text x={SPARK_W - 2} y={46} fill="var(--text-faint)" fontSize={9} textAnchor="end">
        {min.toFixed(0)}%
      </text>
    </svg>
  );
}

export function AccuracyPanel({
  data,
  windowSize = 16,
}: {
  data: AccuracyStats;
  windowSize?: number;
}) {
  const zones: Zone[] = [
    { key: "head", label: "Cabeza", pct: data.head_pct, hits: data.head_hits },
    { key: "body", label: "Torso", pct: data.body_pct, hits: data.body_hits },
    { key: "legs", label: "Piernas", pct: data.legs_pct, hits: data.legs_hits },
  ];
  const colors = zoneColors(zones);
  const totalHits = data.head_hits + data.body_hits + data.legs_hits;

  return (
    <div className="panel-card">
      <div className="panel-title">Precisión</div>
      <div className="panel-subtitle">Últimas {windowSize} partidas</div>
      {totalHits === 0 ? (
        <p className="muted">Todavía no hay impactos registrados en este período.</p>
      ) : (
        <>
          <div className="accuracy-body">
            <AccuracySilhouette
              headColor={colors.head}
              bodyColor={colors.body}
              legsColor={colors.legs}
            />
            <div className="accuracy-zones">
              {zones.map((z) => (
                <div className="accuracy-zone" key={z.key}>
                  <span className="az-label">{z.label}</span>
                  <span className="az-values">
                    <b style={{ color: colors[z.key] }}>{z.pct.toFixed(1)}%</b>
                    <b className="az-hits">{z.hits} hits</b>
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="accuracy-spark-label">HS% promedio por partida</div>
          <Sparkline series={data.hs_pct_series} />
        </>
      )}
    </div>
  );
}
