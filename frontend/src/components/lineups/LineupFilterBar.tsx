import { useMemo } from "react";
import { GrenadeIcon } from "./GrenadeIcon";
import type { Category, MapPin } from "./types";
import type { TeamFilter } from "./mockLineups";

interface LineupFilterBarProps {
  mapName: string;
  allPins: MapPin[];
  activeCategory: Category | "all";
  onCategoryChange: (category: Category | "all") => void;
  activeTeam: TeamFilter;
  onTeamChange: (team: TeamFilter) => void;
}

const CATEGORY_LABEL: Record<Category, string> = {
  smoke: "Smokes",
  flash: "Flashbangs",
  molotov: "Molotovs",
  he: "HE",
};

const CATEGORIES: Category[] = ["smoke", "flash", "molotov", "he"];

export function LineupFilterBar({
  mapName,
  allPins,
  activeCategory,
  onCategoryChange,
  activeTeam,
  onTeamChange,
}: LineupFilterBarProps) {
  // Computar contadores en vivo: la burbuja de categoría filtra por equipo activo.
  const categoryCounts = useMemo(() => {
    const counts: Record<Category | "all", number> = {
      smoke: 0,
      flash: 0,
      molotov: 0,
      he: 0,
      all: 0,
    };

    allPins.forEach((pin) => {
      if (activeTeam === "ANY" || pin.team === activeTeam) {
        counts[pin.category]++;
        counts.all++;
      }
    });

    return counts;
  }, [allPins, activeTeam]);

  return (
    <div className="lme-filterbar">
      <h2 className="lme-filterbar-title">{mapName}</h2>

      <div className="lme-bubble-row">
        <button
          type="button"
          className={`lme-bubble ${activeCategory === "all" ? "active" : ""}`}
          onClick={() => onCategoryChange("all")}
        >
          <span className="lme-bubble-label">Todos</span>
          <span className="lme-bubble-count">{categoryCounts.all}</span>
        </button>

        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`lme-bubble lme-bubble-${cat} ${activeCategory === cat ? "active" : ""}`}
            onClick={() => onCategoryChange(cat)}
          >
            <GrenadeIcon category={cat} size={15} />
            <span className="lme-bubble-label">{CATEGORY_LABEL[cat]}</span>
            <span className="lme-bubble-count">{categoryCounts[cat]}</span>
          </button>
        ))}
      </div>

      <div className="lme-team-pills">
        {(["CT", "T", "ANY"] as const).map((team) => (
          <button
            key={team}
            type="button"
            className={`lme-team-pill ${activeTeam === team ? "active" : ""}`}
            data-team={team}
            onClick={() => onTeamChange(team)}
          >
            {team}
          </button>
        ))}
      </div>
    </div>
  );
}
