import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { staggerList } from "../motion/presets";
import type { MatchHistoryEntry } from "../../types";
import { MatchCard } from "./MatchCard";
import { MatchFilterBar, type MatchTypeTab, type SecondaryFilter } from "./MatchFilterBar";

const PAGE_SIZE = 10;

// rank_type null = demo vieja sin re-ingerir: se muestra en cualquier pestaña
// para no ocultar historial existente (mismo criterio que antes en ProfileView).
function matchesTab(m: MatchHistoryEntry, tab: MatchTypeTab): boolean {
  if (tab === "all" || m.rank_type === null) return true;
  return tab === "premier" ? m.rank_type === 11 : m.rank_type !== 11;
}

function matchesSecondary(m: MatchHistoryEntry, filter: SecondaryFilter): boolean {
  if (filter.kind === "all") return true;
  if (filter.kind === "result") return m.won === filter.won;
  return m.map === filter.map;
}

export function MatchHistory({ matches }: { matches: MatchHistoryEntry[] }) {
  const [tab, setTab] = useState<MatchTypeTab>("all");
  const [secondary, setSecondary] = useState<SecondaryFilter>({ kind: "all" });
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const availableMaps = useMemo(
    () =>
      Array.from(new Set(matches.map((m) => m.map).filter((v): v is string => v !== null))).sort(),
    [matches]
  );

  const filtered = useMemo(
    () => matches.filter((m) => matchesTab(m, tab) && matchesSecondary(m, secondary)),
    [matches, tab, secondary]
  );

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [tab, secondary]);

  return (
    <div className="mh-wrap">
      <MatchFilterBar
        tab={tab}
        onTabChange={setTab}
        secondary={secondary}
        onSecondaryChange={setSecondary}
        availableMaps={availableMaps}
      />
      {filtered.length === 0 ? (
        <p className="muted">No hay partidas para este filtro.</p>
      ) : (
        <motion.div className="mh-list" variants={staggerList} initial="hidden" animate="show">
          {filtered.slice(0, visibleCount).map((m) => (
            <MatchCard key={m.match_id} match={m} />
          ))}
        </motion.div>
      )}
      {visibleCount < filtered.length && (
        <button className="panel-cta" onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}>
          Cargar más partidas
        </button>
      )}
      <div className="mh-note">
        El historial crece con cada demo que ingerís (ver <code>INGESTA_MANUAL.md</code>) — click en
        una tarjeta para ver su Match Detail.
      </div>
    </div>
  );
}
