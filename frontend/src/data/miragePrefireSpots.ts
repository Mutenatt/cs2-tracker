// Coordenadas y ángulos fijos para el minijuego de Prefire/Aim Trainer en
// Mirage. Los valores están calibrados a mano contra mirage_cs2_fps.glb
// (ver public/prefireaim) y no se derivan de ningún dato del backend.

export type Vec3 = [number, number, number];

export interface PrefireSpot {
  /** Identificador estable, usado como key de React y para debug. */
  id: string;
  /** Nombre de callout mostrado en la etiqueta flotante sobre el bot. */
  callout: string;
  position: Vec3;
  /** Rotación en Y (radianes) hacia la que mira el bot al aparecer. */
  rotationY: number;
}

export interface PrefireRoutine {
  id: string;
  label: string;
  /** Punto y orientación donde se teletransporta al jugador al elegir la rutina. */
  playerSpawn: Vec3;
  playerSpawnRotationY: number;
  spots: PrefireSpot[];
}

const A_SITE_SPAWN: Vec3 = [0, 1.6, 15];
const MID_SPAWN: Vec3 = [0, 1.6, 25];
const B_SITE_SPAWN: Vec3 = [-10, 1.6, 0];

export const MIRAGE_PREFIRE_ROUTINES: PrefireRoutine[] = [
  {
    id: "a-site",
    label: "A Site Clear",
    playerSpawn: A_SITE_SPAWN,
    // Los spots quedan todos en Z muy negativo respecto del spawn (Z=15):
    // 0 rad ya mira hacia -Z (forward por defecto de three.js), sin vuelta.
    playerSpawnRotationY: 0,
    spots: [
      { id: "a-sandwich", callout: "SANDWICH", position: [12.5, 1.2, -18.4], rotationY: Math.PI * 0.75 },
      { id: "a-stairs", callout: "STAIRS", position: [14.0, 3.1, -22.0], rotationY: Math.PI * 0.9 },
      { id: "a-jungle", callout: "JUNGLE", position: [8.2, 1.2, -28.5], rotationY: Math.PI },
      { id: "a-ticket", callout: "TICKET / CT", position: [18.0, 1.5, -35.0], rotationY: -Math.PI / 2 },
      { id: "a-firebox", callout: "FIREBOX", position: [2.5, 1.2, -32.0], rotationY: Math.PI * 1.1 },
      { id: "a-ninja", callout: "NINJA", position: [5.0, 1.2, -34.5], rotationY: Math.PI * 1.2 },
      { id: "a-triple", callout: "TRIPLE BOX", position: [10.0, 1.2, -25.0], rotationY: Math.PI },
      { id: "a-under-palace", callout: "UNDER PALACE", position: [-2.0, 1.2, -15.0], rotationY: Math.PI * 0.6 },
    ],
  },
  {
    id: "mid",
    label: "Mid Control",
    playerSpawn: MID_SPAWN,
    // Mismo caso: los spots de mid quedan en Z muy negativo respecto del
    // spawn (Z=25).
    playerSpawnRotationY: 0,
    spots: [
      { id: "mid-sniper-window", callout: "SNIPER WINDOW", position: [0.0, 4.5, -45.0], rotationY: Math.PI },
      { id: "mid-connector", callout: "CONNECTOR", position: [8.5, 2.0, -38.0], rotationY: Math.PI * 1.25 },
      { id: "mid-catwalk", callout: "CATWALK / SHORT", position: [-12.0, 2.5, -35.0], rotationY: Math.PI * 0.75 },
    ],
  },
  {
    id: "b-site",
    label: "B Site Clear",
    playerSpawn: B_SITE_SPAWN,
    // Acá los spots quedan en X muy negativo y Z positivo respecto del spawn
    // (-10, 0): apunta en diagonal hacia ese cuadrante en vez de +Z puro.
    playerSpawnRotationY: Math.PI * 0.75,
    spots: [
      { id: "b-van", callout: "VAN / CAR", position: [-35.0, 1.5, 12.0], rotationY: Math.PI / 2 },
      { id: "b-bench", callout: "BENCH", position: [-42.0, 1.2, 22.0], rotationY: Math.PI / 2 },
      { id: "b-default", callout: "DEFAULT B", position: [-30.0, 1.2, 20.0], rotationY: Math.PI * 1.1 },
      { id: "b-market-window", callout: "MARKET WINDOW", position: [-22.0, 2.8, 30.0], rotationY: Math.PI * 0.8 },
      { id: "b-market-door", callout: "MARKET DOOR", position: [-15.0, 1.2, 28.0], rotationY: Math.PI * 0.9 },
    ],
  },
];

export function getRoutine(id: string): PrefireRoutine | undefined {
  return MIRAGE_PREFIRE_ROUTINES.find((routine) => routine.id === id);
}
