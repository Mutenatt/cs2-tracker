import type { AccuracyStats } from "../types";
import { AccuracySilhouette, type ZoneVisual } from "./AccuracySilhouette";

const SPARK_W = 300;
const SPARK_H = 80;
const SPARK_PAD = 10;

interface Zone {
  key: "head" | "body" | "legs";
  label: string;
  pct: number;
  hits: number;
}

// Mayor % -> verde neón (--go) con glow, segunda -> cian neón (--recon) con
// glow, menor -> gris apagado sin glow. Calculado dinámicamente por ranking,
// no una zona fija por nombre (ver spec: en el ejemplo de referencia esto da
// Torso=verde/Cabeza=cian, pero cambia según los datos reales del jugador).
function zoneVisuals(zones: Zone[]): Record<string, ZoneVisual> {
  const ranked = [...zones].sort((a, b) => b.pct - a.pct);
  const visuals: Record<string, ZoneVisual> = {};
  ranked.forEach((z, i) => {
    visuals[z.key] =
      i === 0
        ? { color: "var(--go)", glow: "go" }
        : i === 1
          ? { color: "var(--recon)", glow: "recon" }
          : { color: "var(--text-faint)", glow: "none" };
  });
  return visuals;
}

function Sparkline({ series }: { series: number[] }) {
  if (series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min;
  const x = (i: number) => SPARK_PAD + (i / (series.length - 1)) * (SPARK_W - 2 * SPARK_PAD);
  const y = (v: number) =>
    span === 0 ? SPARK_H / 2 : SPARK_PAD + ((max - v) / span) * (SPARK_H - 2 * SPARK_PAD);
  const line = series
    .map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`)
    .join(" ");
  const area = `${line} L ${x(series.length - 1).toFixed(1)} ${SPARK_H - SPARK_PAD} L ${x(0)} ${SPARK_H - SPARK_PAD} Z`;

  return (
    <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} style={{ width: "100%", display: "block" }}>
      <defs>
        <linearGradient id="accuracy-spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--recon)" stopOpacity={0.35} />
          <stop offset="100%" stopColor="var(--recon)" stopOpacity={0} />
        </linearGradient>
      </defs>
      <line
        x1={0}
        y1={SPARK_PAD}
        x2={SPARK_W}
        y2={SPARK_PAD}
        stroke="var(--line)"
        strokeOpacity={0.6}
        strokeWidth={1}
      />
      <line
        x1={0}
        y1={SPARK_H - SPARK_PAD}
        x2={SPARK_W}
        y2={SPARK_H - SPARK_PAD}
        stroke="var(--line)"
        strokeOpacity={0.6}
        strokeWidth={1}
      />
      <path d={area} fill="url(#accuracy-spark-fill)" stroke="none" />
      <path d={line} fill="none" stroke="var(--recon)" strokeWidth={2} strokeLinecap="round" />
      <text
        x={SPARK_W - 2}
        y={SPARK_PAD + 10}
        fill="var(--text-faint)"
        fontSize={9}
        textAnchor="end"
      >
        {max.toFixed(0)}%
      </text>
      <text
        x={SPARK_W - 2}
        y={SPARK_H - SPARK_PAD - 3}
        fill="var(--text-faint)"
        fontSize={9}
        textAnchor="end"
      >
        {min.toFixed(0)}%
      </text>
    </svg>
  );
}

export function AccuracyPanel({ data }: { data: AccuracyStats }) {
  const zones: Zone[] = [
    { key: "head", label: "Cabeza", pct: data.head_pct, hits: data.head_hits },
    { key: "body", label: "Torso", pct: data.body_pct, hits: data.body_hits },
    { key: "legs", label: "Piernas", pct: data.legs_pct, hits: data.legs_hits },
  ];
  const visuals = zoneVisuals(zones);
  const totalHits = data.head_hits + data.body_hits + data.legs_hits;

  return (
    <div className="panel-card">
      <div className="panel-title">Precisión</div>
      <div className="panel-subtitle">Total de partidas procesadas</div>
      {totalHits === 0 ? (
        <p className="muted">Todavía no hay impactos registrados en este período.</p>
      ) : (
        <>
          <div className="accuracy-body">
            <AccuracySilhouette head={visuals.head} body={visuals.body} legs={visuals.legs} />
            <div className="accuracy-zones">
              {zones.map((z) => (
                <div className="accuracy-zone" key={z.key}>
                  <div className="az-top">
                    <span className="az-label">{z.label}</span>
                    <b className="az-pct mono" style={{ color: visuals[z.key].color }}>
                      {z.pct.toFixed(1)}%
                    </b>
                  </div>
                  <span className="az-hits">{z.hits} hits</span>
                  <div className="az-bar">
                    <span
                      className="az-bar-fill"
                      style={{ width: `${z.pct}%`, background: visuals[z.key].color }}
                    />
                  </div>
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
