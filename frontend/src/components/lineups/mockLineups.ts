// Datos mock para el prototipo standalone del mapa interactivo de lineups.
// Coordenadas calibradas a ojo contra una grilla de referencia superpuesta
// sobre /public/radar/de_mirage_radar_psd.png (fracción 0-1 por eje),
// cruzadas con la geografía conocida de los callouts de Mirage -- no son
// telemetría real, pero ya no son estimaciones a ciegas.
import type { MapPin, Team } from "./types";

export type { Category, MapPin, Team } from "./types";
export type TeamFilter = Team | "ANY";

export const MOCK_MAP_KEY = "de_mirage";
export const MOCK_MAP_NAME = "Mirage";

export const MOCK_LINEUPS: MapPin[] = [
  {
    id: "mirage-ct-he-caverna",
    category: "he",
    team: "CT",
    label: "Caverna",
    startX: 0.62,
    startY: 0.2,
    x: 0.44,
    y: 0.23,
    videoUrl: "/lineups/de_mirage/ct/deto-ct-caverna.mp4",
    instructions: "Left Click / Stationary",
    crosshairNote:
      "Alineá la mira con el borde superior del arco de Caverna, apenas por encima de la textura clara.",
  },
  {
    id: "mirage-t-he-caverna",
    category: "he",
    team: "T",
    // No hay clip de HE para T en disco todavía -- se reutiliza el de CT
    // como placeholder visual hasta grabar el real.
    label: "Caverna (variante T)",
    startX: 0.5,
    startY: 0.45,
    x: 0.44,
    y: 0.23,
    videoUrl: "/lineups/de_mirage/ct/deto-ct-caverna.mp4",
    instructions: "Run Throw",
    crosshairNote: "Corré en línea recta hacia el cartel de Caverna y soltá justo antes de frenar.",
  },
  {
    id: "mirage-ct-moli-tapete",
    category: "molotov",
    team: "CT",
    label: "Tapete",
    startX: 0.55,
    startY: 0.22,
    x: 0.22,
    y: 0.31,
    videoUrl: "/lineups/de_mirage/ct/moli-ct-tapete.mp4",
    instructions: "Left Click / Stationary",
    crosshairNote:
      "Parate pegado a la reja y apuntá al vértice donde el techo del tapete corta la pared.",
  },
  {
    id: "mirage-t-moli-van",
    category: "molotov",
    team: "T",
    label: "Van",
    startX: 0.35,
    startY: 0.78,
    x: 0.46,
    y: 0.64,
    videoUrl: "/lineups/de_mirage/t/moli-van.mp4",
    instructions: "Jumpthrow",
    crosshairNote:
      "Mirá al techo, alineado con el segundo panel de chapa contando desde la esquina del van.",
  },
  {
    id: "mirage-ct-flash-medio",
    category: "flash",
    team: "CT",
    label: "Medio",
    startX: 0.5,
    startY: 0.3,
    x: 0.56,
    y: 0.46,
    videoUrl: "/lineups/de_mirage/ct/popflash-ct-medio.mp4",
    instructions: "Left Click / Crouch",
    crosshairNote:
      "Agachado contra la baranda, apuntá al farol que cuelga sobre la entrada a medio.",
  },
  {
    id: "mirage-t-flash-a",
    category: "flash",
    team: "T",
    label: "A",
    startX: 0.3,
    startY: 0.55,
    x: 0.235,
    y: 0.285,
    videoUrl: "/lineups/de_mirage/t/popflash-A.mp4",
    instructions: "Jumpthrow",
    crosshairNote:
      "Saltá de espaldas a la rampa y mirá justo al borde del cartel de A antes de soltar.",
  },
  {
    id: "mirage-ct-smoke-l",
    category: "smoke",
    team: "CT",
    label: "Zona L",
    startX: 0.55,
    startY: 0.25,
    x: 0.62,
    y: 0.42,
    videoUrl: "/lineups/de_mirage/ct/smoke-ct-L.mp4",
    instructions: "Left Click / Stationary",
    crosshairNote:
      "Parado en el borde del pixel específico junto al cajón, apuntá a la punta de la antena de fondo.",
  },
  {
    id: "mirage-t-smoke-jungle",
    category: "smoke",
    team: "T",
    label: "Jungle",
    startX: 0.38,
    startY: 0.75,
    x: 0.17,
    y: 0.56,
    videoUrl: "/lineups/de_mirage/t/smoke-jungle.mp4",
    instructions: "Jumpthrow",
    crosshairNote:
      "De espaldas al árbol seco, mirá al punto donde la copa del árbol de jungle toca el cielo.",
  },
  {
    id: "mirage-t-smoke-window",
    category: "smoke",
    team: "T",
    label: "B Window",
    startX: 0.42,
    startY: 0.62,
    x: 0.5,
    y: 0.72,
    videoUrl: "/lineups/de_mirage/t/smoke-b-window.mp4",
    instructions: "Run Throw",
    crosshairNote:
      "Corriendo desde B apps, soltá con la mira apuntando al marco superior de la ventana.",
  },
];
