export type Category = "smoke" | "flash" | "molotov" | "he";
export type Team = "CT" | "T";

export interface MapPin {
  id: string;
  category: Category;
  team?: Team;
  label: string;
  x: number;
  y: number;
  startX?: number;
  startY?: number;
  videoUrl: string;
  instructions?: string;
  crosshairNote?: string;
}
