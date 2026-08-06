// Datos mock para el prototipo standalone del mapa interactivo de lineups.
// Coordenadas u/v ilustrativas (aproximadas a ojo sobre el radar de Mirage),
// no derivadas de telemetría real -- ajustar visualmente si se integra.

export type Category = "smoke" | "flash" | "molotov" | "he";
export type Team = "CT" | "T";
export type TeamFilter = Team | "ANY";

export interface LineupPin {
  id: string;
  mapKey: string;
  category: Category;
  team: Team;
  label: string;
  startU: number;
  startV: number;
  endU: number;
  endV: number;
  videoUrl: string;
  instructions: string;
}

export const MOCK_MAP_KEY = "de_mirage";
export const MOCK_MAP_NAME = "Mirage";

export const MOCK_LINEUPS: LineupPin[] = [
  {
    id: "mirage-ct-he-caverna",
    mapKey: MOCK_MAP_KEY,
    category: "he",
    team: "CT",
    label: "Caverna",
    startU: 0.58,
    startV: 0.22,
    endU: 0.74,
    endV: 0.3,
    videoUrl: "/lineups/de_mirage/ct/deto-ct-caverna.mp4",
    instructions: "Left Click / Stationary",
  },
  {
    id: "mirage-t-he-caverna",
    mapKey: MOCK_MAP_KEY,
    category: "he",
    team: "T",
    // No hay clip de HE para T en disco todavía -- se reutiliza el de CT
    // como placeholder visual hasta grabar el real.
    label: "Caverna (variante T)",
    startU: 0.45,
    startV: 0.68,
    endU: 0.74,
    endV: 0.3,
    videoUrl: "/lineups/de_mirage/ct/deto-ct-caverna.mp4",
    instructions: "Run Throw",
  },
  {
    id: "mirage-ct-moli-tapete",
    mapKey: MOCK_MAP_KEY,
    category: "molotov",
    team: "CT",
    label: "Tapete",
    startU: 0.6,
    startV: 0.24,
    endU: 0.52,
    endV: 0.34,
    videoUrl: "/lineups/de_mirage/ct/moli-ct-tapete.mp4",
    instructions: "Left Click / Stationary",
  },
  {
    id: "mirage-t-moli-van",
    mapKey: MOCK_MAP_KEY,
    category: "molotov",
    team: "T",
    label: "Van",
    startU: 0.4,
    startV: 0.72,
    endU: 0.34,
    endV: 0.5,
    videoUrl: "/lineups/de_mirage/t/moli-van.mp4",
    instructions: "Jumpthrow",
  },
  {
    id: "mirage-ct-flash-medio",
    mapKey: MOCK_MAP_KEY,
    category: "flash",
    team: "CT",
    label: "Medio",
    startU: 0.55,
    startV: 0.3,
    endU: 0.44,
    endV: 0.46,
    videoUrl: "/lineups/de_mirage/ct/popflash-ct-medio.mp4",
    instructions: "Left Click / Crouch",
  },
  {
    id: "mirage-t-flash-a",
    mapKey: MOCK_MAP_KEY,
    category: "flash",
    team: "T",
    label: "A",
    startU: 0.62,
    startV: 0.66,
    endU: 0.78,
    endV: 0.28,
    videoUrl: "/lineups/de_mirage/t/popflash-A.mp4",
    instructions: "Jumpthrow",
  },
  {
    id: "mirage-ct-smoke-l",
    mapKey: MOCK_MAP_KEY,
    category: "smoke",
    team: "CT",
    label: "Zona L",
    startU: 0.57,
    startV: 0.26,
    endU: 0.66,
    endV: 0.38,
    videoUrl: "/lineups/de_mirage/ct/smoke-ct-L.mp4",
    instructions: "Left Click / Stationary",
  },
  {
    id: "mirage-t-smoke-jungle",
    mapKey: MOCK_MAP_KEY,
    category: "smoke",
    team: "T",
    label: "Jungle",
    startU: 0.42,
    startV: 0.7,
    endU: 0.22,
    endV: 0.62,
    videoUrl: "/lineups/de_mirage/t/smoke-jungle.mp4",
    instructions: "Jumpthrow",
  },
  {
    id: "mirage-t-smoke-window",
    mapKey: MOCK_MAP_KEY,
    category: "smoke",
    team: "T",
    label: "B Window",
    startU: 0.2,
    startV: 0.58,
    endU: 0.18,
    endV: 0.4,
    videoUrl: "/lineups/de_mirage/t/smoke-b-window.mp4",
    instructions: "Run Throw",
  },
];
