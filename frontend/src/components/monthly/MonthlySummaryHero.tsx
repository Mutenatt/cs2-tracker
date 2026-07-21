import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { getMonthlySummary } from "../../api";
import { useUser } from "../../context/UserContext";
import { Button } from "../Button";
import { Card } from "../Card";
import { CrosshairIcon } from "../CrosshairIcon";
import { SectionLabel } from "../SectionLabel";
import { CARD_DURATION } from "../motion/presets";
import { MatchesPerDayChart } from "./MatchesPerDayChart";
import { StatCard } from "./StatCard";
import type { MonthlySummaryResponse } from "../../types";

export function MonthlySummaryHero() {
  const user = useUser();
  const [data, setData] = useState<MonthlySummaryResponse | null>(null);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setData(await getMonthlySummary(user.steamid));
      } catch {
        setError(true);
      }
    })();
  }, [user.steamid]);

  if (error) return null; // igual que streams/ranking: si falla, no rompe la Home
  if (data === null) {
    return (
      <Card className="monthly-hero">
        <span className="cs-section-label">Cargando tu resumen mensual…</span>
      </Card>
    );
  }

  const empty = data.totals.matches === 0;

  return (
    <Card className="monthly-hero">
      <div className="monthly-hero-diag" aria-hidden="true" />
      <div className="monthly-hero-head">
        <div className="monthly-hero-headline">
          <h2 className="monthly-hero-title">Tu rendimiento este mes</h2>
          <p className="monthly-hero-sub">
            {empty
              ? "Sin partidas este mes todavía."
              : `${data.totals.matches} partidas · ${data.totals.winrate}% winrate · K/D ${data.totals.kd.toFixed(2)}`}
          </p>
          {!empty && (
            <Button variant={expanded ? "ghost" : "primary"} onClick={() => setExpanded((v) => !v)}>
              {expanded ? "Ocultar detalles" : "Ver detalles"}{" "}
              <span className={`monthly-caret${expanded ? " up" : ""}`} aria-hidden="true">
                ▾
              </span>
            </Button>
          )}
        </div>
        {!empty && (
          <div className="monthly-hero-stats">
            <StatCard value={`${data.headline.best_streak_wins}W`} label="Mejor racha" />
            <StatCard value={data.headline.rating.toFixed(2)} label="Rating" />
            <StatCard value={`${data.headline.hs_pct}%`} label="HS %" />
          </div>
        )}
        <CrosshairIcon size={120} className="monthly-hero-crosshair" />
      </div>

      <AnimatePresence initial={false}>
        {expanded && !empty && (
          <motion.div
            className="monthly-hero-detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: CARD_DURATION, ease: "easeOut" }}
          >
            <div className="monthly-stat-grid">
              <StatCard value={data.detail.adr_avg.toFixed(1)} label="ADR promedio" />
              <StatCard value={`${data.detail.kast_pct}%`} label="KAST" />
              <StatCard value={String(data.detail.clutches_won)} label="Clutches ganados" />
              <StatCard value={String(data.detail.entry_kills)} label="Entry kills" />
            </div>

            <SectionLabel>Partidas por día</SectionLabel>
            <MatchesPerDayChart data={data.detail.matches_per_day} />

            <div className="monthly-detail-cols">
              <div>
                <SectionLabel>Top 3 mapas</SectionLabel>
                <ul className="monthly-top-maps">
                  {data.detail.top_maps.map((m) => (
                    <li key={m.map_id}>
                      <span>{m.map_id}</span>
                      <span>
                        {m.wins}W-{m.losses}D
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              {data.detail.mvp && (
                <div>
                  <SectionLabel>MVP del mes</SectionLabel>
                  <div className="monthly-mvp-card">
                    <div className="monthly-mvp-thumb" aria-hidden="true" />
                    <div>
                      <div className="monthly-mvp-title">
                        {data.detail.mvp.map_id} · Ronda {data.detail.mvp.round}
                      </div>
                      <div className="monthly-mvp-sub">
                        Clutch 1v{data.detail.mvp.clutch_size} · {data.detail.mvp.kills_in_round}{" "}
                        kills en la ronda
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
