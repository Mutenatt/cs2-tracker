import generated from "./lineups.json";

export type Side = "T" | "CT" | "BOTH" | "RETAKE";
export type Category = "smoke" | "flash" | "molotov" | "he";

export interface LineupItem {
  id: string;
  title: string;
  side: Side;
  category: Category;
  to: string;
  from?: string;
  video: string;
  notes?: string;
}

// lineups.json lo genera backend/scripts/upload_lineups.py a partir del nombre
// de cada .mp4 de frontend/public/lineups/. resolveJsonModule infiere `string`
// para side/category, así que el cast va acá, una sola vez, en vez de en cada
// componente que lo consuma. Si el JSON trae un valor fuera de las uniones es
// porque el generador cambió: arreglar allá, no acá.
export const GENERATED_LINEUPS = generated as Record<string, LineupItem[]>;
