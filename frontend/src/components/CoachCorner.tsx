import type { CoachInsight } from "../types";

export function CoachCorner({ insights }: { insights: CoachInsight[] }) {
  if (insights.length === 0) return null;
  const matchesAnalyzed = insights[0].matches_analyzed;

  return (
    <>
      <div className="section-head">
        <span className="display">Coach's Corner</span>
        <span className="rule" />
      </div>
      <div className="coach-card">
        <div className="ch">
          <span className="cdot" />
          ANÁLISIS DE TUS ÚLTIMAS {matchesAnalyzed} PARTIDA{matchesAnalyzed === 1 ? "" : "S"}
        </div>
        {insights.map((ins, i) => (
          <div className={`coach-line${ins.low_confidence ? " low-data" : ""}`} key={i}>
            <span className="cy">›</span>
            <span>
              <b>Muertes tempranas de ronda:</b> {ins.text}{" "}
              {ins.low_confidence && <span className="illus-tag">dato real, baja confianza</span>}
            </span>
          </div>
        ))}
      </div>
      <div className="section-note" style={{ marginTop: 8 }}>
        Análisis real sobre <code>seconds_into_round</code> (calculado con el tick de fin de
        freezetime del demo). Con menos de 8 partidas ingeridas se marca como baja confianza — ni
        confirma ni descarta el patrón, pero el número en sí es real.
      </div>
    </>
  );
}
