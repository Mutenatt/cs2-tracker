// Equivalencia entre CS Rating Premier y los rangos clásicos de CS:GO.
// Umbrales tomados de equivalencias_rangos_csgo_cs2.md (estimados por el
// usuario, no una fuente oficial de Valve). Coinciden con los cortes de
// tier t1-t7 que ya usa RankBadge.tsx (0/5000/10000/15000/20000/25000/30000)
// -- los hex reusan esa misma paleta. "Legendary Eagle" aparece dos veces
// a propósito: mismo nombre y rankId (mismo ícono), pero el doc lo separa en
// dos bandas de rating que caen en tiers de color distintos (t4 por debajo
// de 20000, t5 desde ahí), igual que ya le pasa al número de Premier Rating
// del hero.
// Íconos: insignias oficiales de Valve en frontend/public/matchmakingcsgo/
// (`{rankId}.svg`, rank_id estándar de CS:GO, 1=Silver I .. 18=Global Elite).
export interface CsgoRank {
  name: string;
  min: number;
  max: number;
  hex: string;
  rankId: number;
}

export const CSGO_RANKS: CsgoRank[] = [
  { name: "Silver I", min: 0, max: 800, hex: "#b0c3d9", rankId: 1 },
  { name: "Silver II", min: 800, max: 1600, hex: "#b0c3d9", rankId: 2 },
  { name: "Silver III", min: 1600, max: 2400, hex: "#b0c3d9", rankId: 3 },
  { name: "Silver IV", min: 2400, max: 3200, hex: "#b0c3d9", rankId: 4 },
  { name: "Silver Elite", min: 3200, max: 4000, hex: "#b0c3d9", rankId: 5 },
  {
    name: "Silver Elite Master",
    min: 4000,
    max: 5000,
    hex: "#b0c3d9",
    rankId: 6,
  },
  { name: "Gold Nova I", min: 5000, max: 6250, hex: "#5e98d9", rankId: 7 },
  { name: "Gold Nova II", min: 6250, max: 7500, hex: "#5e98d9", rankId: 8 },
  { name: "Gold Nova III", min: 7500, max: 8750, hex: "#5e98d9", rankId: 9 },
  { name: "Gold Nova Master", min: 8750, max: 10000, hex: "#5e98d9", rankId: 10 },
  {
    name: "Master Guardian I",
    min: 10000,
    max: 11651,
    hex: "#6a8bff",
    rankId: 11,
  },
  {
    name: "Master Guardian II",
    min: 11651,
    max: 13301,
    hex: "#6a8bff",
    rankId: 12,
  },
  {
    name: "Master Guardian Elite",
    min: 13301,
    max: 15000,
    hex: "#6a8bff",
    rankId: 13,
  },
  {
    name: "Distinguished Master Guardian",
    min: 15000,
    max: 17500,
    hex: "#a86aff",
    rankId: 14,
  },
  { name: "Legendary Eagle", min: 17500, max: 20000, hex: "#a86aff", rankId: 15 },
  { name: "Legendary Eagle", min: 20000, max: 22500, hex: "#d32ce6", rankId: 15 },
  {
    name: "Legendary Eagle Master",
    min: 22500,
    max: 25000,
    hex: "#d32ce6",
    rankId: 16,
  },
  {
    name: "Supreme Master First Class",
    min: 25000,
    max: 30000,
    hex: "#eb4b4b",
    rankId: 17,
  },
  { name: "Global Elite", min: 30000, max: Infinity, hex: "#e4ae39", rankId: 18 },
];

export function csgoRankFor(premierRating: number): CsgoRank {
  return (
    CSGO_RANKS.find((r) => premierRating >= r.min && premierRating < r.max) ??
    CSGO_RANKS[CSGO_RANKS.length - 1]
  );
}

export function RankCrest({ rank }: { rank: CsgoRank }) {
  return (
    <img
      className="rank-crest"
      src={`/matchmakingcsgo/${rank.rankId}.svg`}
      alt={rank.name}
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}
