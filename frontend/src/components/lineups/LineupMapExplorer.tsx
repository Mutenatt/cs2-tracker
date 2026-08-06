import { useMemo, useState } from "react";
import { LineupSidebar } from "./LineupSidebar";
import { LineupMapStage } from "./LineupMapStage";
import {
  MOCK_LINEUPS,
  MOCK_MAP_KEY,
  MOCK_MAP_NAME,
  type Category,
  type TeamFilter,
} from "./mockLineups";

export function LineupMapExplorer() {
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");
  const [activeTeam, setActiveTeam] = useState<TeamFilter>("ANY");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return MOCK_LINEUPS.filter((pin) => {
      const categoryMatch = activeCategory === "all" || pin.category === activeCategory;
      const teamMatch = activeTeam === "ANY" || pin.team === activeTeam;
      return categoryMatch && teamMatch;
    });
  }, [activeCategory, activeTeam]);

  const hoveredLineup = useMemo(
    () => filtered.find((p) => p.id === hoveredId) ?? null,
    [filtered, hoveredId]
  );

  return (
    <div className="lme-shell">
      <LineupSidebar
        mapName={MOCK_MAP_NAME}
        allPins={MOCK_LINEUPS}
        activeCategory={activeCategory}
        onCategoryChange={setActiveCategory}
        activeTeam={activeTeam}
        onTeamChange={setActiveTeam}
      />
      <LineupMapStage
        mapKey={MOCK_MAP_KEY}
        pins={filtered}
        hoveredLineup={hoveredLineup}
        onPinEnter={setHoveredId}
        onPinLeave={() => setHoveredId(null)}
      />
    </div>
  );
}
