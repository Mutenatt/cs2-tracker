import * as THREE from "three";
import type { PrefireRoutine, Vec3 } from "../../data/miragePrefireSpots";

// El .glb de Mirage no está normalizado a "floor = 0": su origen de mundo
// real (post node-transforms del GLTF) cae en cualquier Y según la zona.
// Los X/Z de miragePrefireSpots.ts son la fuente de verdad para el layout
// horizontal de cada callout, pero el Y se recalcula acá con un raycast
// hacia abajo contra la geometría real del mapa -- así el jugador/bot
// siempre aparece parado sobre el piso real en vez de enterrado en una
// pared o flotando en el vacío por una Y inventada a mano.
const raycaster = new THREE.Raycaster();
const DOWN = new THREE.Vector3(0, -1, 0);

/**
 * Tira un rayo hacia abajo desde `aboveY` y devuelve la Y del primer punto
 * de impacto contra el mapa. CRÍTICO: `aboveY` tiene que ser una altura ya
 * cercana a la real (la Y actual del jugador, o la Y estimada del spot +
 * un margen chico) -- si arranca desde el techo de TODO el mapa (como hacía
 * antes), el rayo puede "ver a través" del techo de un edificio de varios
 * pisos y devolver la altura de ESE techo en vez del piso interior real,
 * dejando al jugador/bot enterrado en la losa. Un margen chico y local
 * evita eso.
 */
export function findGroundY(mapScene: THREE.Object3D, x: number, z: number, aboveY: number, fallbackY: number): number {
  raycaster.set(new THREE.Vector3(x, aboveY, z), DOWN);
  const hits = raycaster.intersectObject(mapScene, true);
  return hits.length > 0 ? hits[0].point.y : fallbackY;
}

// Margen sobre la Y "adivinada" a mano en miragePrefireSpots.ts -- suficiente
// para cubrir el error de calibración manual sin llegar a atravesar el techo
// de un edificio de otro piso.
const SPAWN_RAY_MARGIN = 8;

export function snapRoutineToGround(routine: PrefireRoutine, mapScene: THREE.Object3D, eyeHeight: number): PrefireRoutine {
  mapScene.updateMatrixWorld(true);

  const groundedSpawn: Vec3 = [
    routine.playerSpawn[0],
    findGroundY(
      mapScene,
      routine.playerSpawn[0],
      routine.playerSpawn[2],
      routine.playerSpawn[1] + SPAWN_RAY_MARGIN,
      routine.playerSpawn[1],
    ) + eyeHeight,
    routine.playerSpawn[2],
  ];

  return {
    ...routine,
    playerSpawn: groundedSpawn,
    spots: routine.spots.map((spot) => ({
      ...spot,
      position: [
        spot.position[0],
        findGroundY(mapScene, spot.position[0], spot.position[2], spot.position[1] + SPAWN_RAY_MARGIN, spot.position[1]),
        spot.position[2],
      ],
    })),
  };
}
