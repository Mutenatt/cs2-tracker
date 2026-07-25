import type { WeaponCategory } from "../types";

// Perfiles genéricos por categoría (line-art, no son assets oficiales del
// juego) -- un ícono por categoría, no por arma individual.
const PATHS: Record<WeaponCategory, string> = {
  rifle: "M2 16 L44 16 L44 10 L52 10 L52 6 L58 6 M14 16 L14 22",
  smg: "M2 16 L38 16 L38 10 L46 10 L46 6 L52 6 M10 16 L10 21",
  pistol: "M8 18 L38 18 L38 8 L44 8",
  sniper: "M2 14 L54 14 M40 14 L40 8 L58 8 M18 14 L18 22",
  shotgun: "M2 17 L48 17 L48 12 L58 12 M20 17 L20 23 M10 17 L10 22",
  heavy: "M2 15 L44 15 L44 9 L52 9 L52 5 L58 5 M10 15 L6 22 L18 22 L14 15",
  melee: "M4 20 L30 6 L36 4 L38 8 L14 22 Z M4 20 L2 22",
};

export function WeaponCategoryIcon({
  category,
  width = 40,
  height = 16,
}: {
  category: WeaponCategory;
  width?: number;
  height?: number;
}) {
  return (
    <svg viewBox="0 0 60 24" style={{ width, height }}>
      <path d={PATHS[category] ?? PATHS.rifle} fill="none" stroke="#8b95a7" strokeWidth={2} />
    </svg>
  );
}
