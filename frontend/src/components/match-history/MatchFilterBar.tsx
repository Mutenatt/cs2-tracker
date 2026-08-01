export type MatchTypeTab = "all" | "premier" | "competitivo";

export type SecondaryFilter =
  { kind: "all" } | { kind: "result"; won: boolean } | { kind: "map"; map: string };

const TABS: { key: MatchTypeTab; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "premier", label: "Premier" },
  { key: "competitivo", label: "Competitivo" },
];

function encodeSecondary(f: SecondaryFilter): string {
  if (f.kind === "all") return "all";
  if (f.kind === "result") return `result:${f.won ? "win" : "loss"}`;
  return `map:${f.map}`;
}

function decodeSecondary(value: string): SecondaryFilter {
  if (value === "result:win") return { kind: "result", won: true };
  if (value === "result:loss") return { kind: "result", won: false };
  if (value.startsWith("map:")) return { kind: "map", map: value.slice(4) };
  return { kind: "all" };
}

export function MatchFilterBar({
  tab,
  onTabChange,
  secondary,
  onSecondaryChange,
  availableMaps,
}: {
  tab: MatchTypeTab;
  onTabChange: (tab: MatchTypeTab) => void;
  secondary: SecondaryFilter;
  onSecondaryChange: (filter: SecondaryFilter) => void;
  availableMaps: string[];
}) {
  return (
    <div className="mh-filterbar">
      <div className="mh-tabs" role="tablist" aria-label="Filtrar por tipo de partida">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`mh-tab${tab === t.key ? " active" : ""}`}
            onClick={() => onTabChange(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <select
        className="mh-secondary-select"
        aria-label="Filtrar por mapa o resultado"
        value={encodeSecondary(secondary)}
        onChange={(e) => onSecondaryChange(decodeSecondary(e.target.value))}
      >
        <option value="all">Todos los mapas</option>
        <optgroup label="Resultado">
          <option value="result:win">Victorias</option>
          <option value="result:loss">Derrotas</option>
        </optgroup>
        {availableMaps.length > 0 && (
          <optgroup label="Mapa">
            {availableMaps.map((map) => (
              <option key={map} value={`map:${map}`}>
                {map.replace(/^de_/, "")}
              </option>
            ))}
          </optgroup>
        )}
      </select>
    </div>
  );
}
