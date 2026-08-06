import { useMemo } from "react";
import { GrenadeIcon } from "./GrenadeIcon";
import type { Category, LineupPin, TeamFilter } from "./mockLineups";

interface LineupSidebarProps {
  mapName: string;
  allPins: LineupPin[];
  activeCategory: Category | "all";
  onCategoryChange: (category: Category | "all") => void;
  activeTeam: TeamFilter;
  onTeamChange: (team: TeamFilter) => void;
}

const CATEGORY_LABEL: Record<Category, string> = {
  smoke: "Humo",
  flash: "Flash",
  molotov: "Molotov",
  he: "Granada HE",
};

const CATEGORIES: Category[] = ["smoke", "flash", "molotov", "he"];

export function LineupSidebar({
  mapName,
  allPins,
  activeCategory,
  onCategoryChange,
  activeTeam,
  onTeamChange,
}: LineupSidebarProps) {
  // Computar contadores en vivo: categoría filtra por equipo activo.
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
    <aside className="lme-sidebar">
      <h2 className="lme-sidebar-title">{mapName}</h2>

      <div className="lme-category-list">
        <button
          className={`lme-category-row ${activeCategory === "all" ? "active" : ""}`}
          onClick={() => onCategoryChange("all")}
        >
          <span className="lme-category-label">Todas</span>
          <span className="lme-category-count">{categoryCounts.all}</span>
        </button>

        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={`lme-category-row lme-category-row-${cat} ${
              activeCategory === cat ? "active" : ""
            }`}
            onClick={() => onCategoryChange(cat)}
          >
            <GrenadeIcon category={cat} size={14} />
            <span className="lme-category-label">{CATEGORY_LABEL[cat]}</span>
            <span className="lme-category-count">{categoryCounts[cat]}</span>
          </button>
        ))}
      </div>

      <div className="lme-team-pills">
        {(["CT", "T", "ANY"] as const).map((team) => (
          <button
            key={team}
            className={`lme-team-pill ${activeTeam === team ? "active" : ""}`}
            data-team={team}
            onClick={() => onTeamChange(team)}
          >
            {team}
          </button>
        ))}
      </div>
    </aside>
  );
}
