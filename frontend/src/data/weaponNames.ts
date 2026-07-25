// Nombres "lindos" y etiquetas de categoría para armas -- compartido entre
// TopWeaponsPanel (top-5 del perfil) y WeaponsView (landing completa), así
// no se duplica ni se desincroniza.
export const NICE_WEAPON_NAME: Record<string, string> = {
  ak47: "AK-47",
  m4a1: "M4A4",
  m4a1_silencer: "M4A1-S",
  awp: "AWP",
  hkp2000: "USP/P2000",
  glock: "Glock",
  deagle: "Desert Eagle",
  usp_silencer: "USP-S",
  galilar: "Galil",
  famas: "FAMAS",
  mp9: "MP9",
  negev: "Negev",
  knife: "Cuchillo",
};

export function niceWeaponName(w: string): string {
  return NICE_WEAPON_NAME[w] ?? w;
}

export const WEAPON_CATEGORY_LABEL: Record<string, string> = {
  rifle: "Rifles de asalto",
  pistol: "Armas secundarias",
  smg: "Subfusiles",
  sniper: "Rifles de precisión",
  shotgun: "Escopetas",
  heavy: "Armas pesadas",
  melee: "Cuerpo a cuerpo",
};
