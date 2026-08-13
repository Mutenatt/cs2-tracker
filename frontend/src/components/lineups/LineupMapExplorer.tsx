import { useMemo, useState } from "react";
import { LineupFilterBar } from "./LineupFilterBar";
import { LineupMapStage } from "./LineupMapStage";
import { LineupVideoModal } from "./LineupVideoModal";
import { LineupCoordEditor } from "./LineupCoordEditor";
import { MOCK_LINEUPS, MOCK_MAP_KEY, MOCK_MAP_NAME, type TeamFilter } from "./mockLineups";
import type { Category, MapPin } from "./types";

export function LineupMapExplorer() {
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");
  const [activeTeam, setActiveTeam] = useState<TeamFilter>("ANY");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedPin, setSelectedPin] = useState<MapPin | null>(null);
  const [editingCoords, setEditingCoords] = useState(false);
  const [coordOverrides, setCoordOverrides] = useState<Record<string, { x: number; y: number }>>(
    {}
  );

  const filtered = useMemo(() => {
    return MOCK_LINEUPS.filter((pin) => {
      const categoryMatch = activeCategory === "all" || pin.category === activeCategory;
      const teamMatch = activeTeam === "ANY" || pin.team === activeTeam;
      return categoryMatch && teamMatch;
    });
  }, [activeCategory, activeTeam]);

  const displayed = useMemo(
    () =>
      filtered.map((pin) => (coordOverrides[pin.id] ? { ...pin, ...coordOverrides[pin.id] } : pin)),
    [filtered, coordOverrides]
  );

  const handlePinDrag = (id: string, x: number, y: number) => {
    setCoordOverrides((prev) => ({ ...prev, [id]: { x, y } }));
  };

  return (
    <div className="lme-shell">
      <LineupFilterBar
        mapName={MOCK_MAP_NAME}
        allPins={MOCK_LINEUPS}
        activeCategory={activeCategory}
        onCategoryChange={setActiveCategory}
        activeTeam={activeTeam}
        onTeamChange={setActiveTeam}
      />

      <LineupCoordEditor
        pins={displayed}
        editing={editingCoords}
        onToggle={() => setEditingCoords((v) => !v)}
      />

      <LineupMapStage
        mapKey={MOCK_MAP_KEY}
        pins={displayed}
        hoveredId={hoveredId}
        onPinHoverStart={setHoveredId}
        onPinHoverEnd={() => setHoveredId(null)}
        onPinSelect={setSelectedPin}
        editable={editingCoords}
        onPinDrag={handlePinDrag}
      />

      {selectedPin && <LineupVideoModal pin={selectedPin} onClose={() => setSelectedPin(null)} />}
    </div>
  );
}
