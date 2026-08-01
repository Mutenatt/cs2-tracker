import { useEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { SkeletonUtils } from "three-stdlib";

export type WeaponId = "ak47" | "karambit";

export const AK47_MODEL_URL = "/models/csgo_ak-47_pov_with_arms.glb";
export const KARAMBIT_MODEL_URL = "/models/cs_go_karambit_with_sport_gloves.glb";

interface WeaponDef {
  id: WeaponId;
  label: string;
  hudIcon: string;
  hotkeyLabel: string;
  modelUrl: string;
  basePosition: THREE.Vector3;
  rotationY: number;
  // Cada .glb trae su propia convención de unidades (Hammer units, cm, etc.)
  // -- esto es lo único que hay que recalibrar a ojo por modelo nuevo.
  scale: number;
  swayAmount: number;
  swaySpeed: number;
  // Offset y rotación que se suman en el pico del "kick" (recoil de disparo
  // para el arma de fuego, golpe/swing para el cuchillo) y decaen solos.
  kickPosition: THREE.Vector3;
  kickRotationX: number;
  kickRecoverySpeed: number;
}

const FOLLOW_SPEED = 10;

/**
 * Bounding box "de verdad" del modelo, ignorando mallas degeneradas/marker
 * (ej. un gizmo o punto de referencia casi sin volumen cerca del origen que
 * algunos exports de Sketchfab dejan sueltos). Sin este filtro, esas mallas
 * arrastran el centro calculado lejos del cluster real de geometría visible
 * -- el arma queda recentrada mal y se ve chica/desplazada aunque la escala
 * esté bien.
 */
function computeSignificantBoundingBox(root: THREE.Object3D): THREE.Box3 {
  root.updateMatrixWorld(true);
  const meshBoxes: { box: THREE.Box3; diagonal: number }[] = [];
  root.traverse((obj) => {
    if ((obj as THREE.Mesh).isMesh) {
      const box = new THREE.Box3().setFromObject(obj);
      meshBoxes.push({ box, diagonal: box.getSize(new THREE.Vector3()).length() });
    }
  });
  if (meshBoxes.length === 0) return new THREE.Box3().setFromObject(root);

  const maxDiagonal = Math.max(...meshBoxes.map((m) => m.diagonal));
  const threshold = maxDiagonal * 0.1;
  const combined = new THREE.Box3();
  for (const { box, diagonal } of meshBoxes) {
    if (diagonal >= threshold) combined.union(box);
  }
  return combined;
}

// Offset local respecto de la cámara y factor de escala por arma. Si un
// .glb nuevo se ve desfasado/gigante, este es el único punto a retocar --
// el recentrado de origen (ver WeaponModel) ya corrige el resto.
export const WEAPON_DEFS: Record<WeaponId, WeaponDef> = {
  ak47: {
    id: "ak47",
    label: "AK-47",
    hudIcon: "🔫",
    hotkeyLabel: "1",
    modelUrl: AK47_MODEL_URL,
    basePosition: new THREE.Vector3(0.14, -0.16, -0.32),
    rotationY: Math.PI,
    // El .glb viene ~26 unidades de largo en su escala nativa (bounding box
    // real, no la del buffer crudo): sin este factor la cámara queda
    // literalmente adentro del arma.
    scale: 0.045,
    swayAmount: 0.012,
    swaySpeed: 6.5,
    kickPosition: new THREE.Vector3(0, 0, 0.09),
    kickRotationX: -0.05,
    kickRecoverySpeed: 10,
  },
  karambit: {
    id: "karambit",
    label: "Karambit",
    hudIcon: "🔪",
    hotkeyLabel: "3",
    modelUrl: KARAMBIT_MODEL_URL,
    basePosition: new THREE.Vector3(0.1, -0.2, -0.3),
    rotationY: Math.PI,
    scale: 0.055,
    // Sway más corto/rápido: un cuchillo se siente más liviano que el rifle.
    swayAmount: 0.01,
    swaySpeed: 7.5,
    // El "kick" del cuchillo es un tajo hacia adelante (Z negativo empuja
    // hacia la pantalla) en vez de un retroceso hacia atrás.
    kickPosition: new THREE.Vector3(0.03, -0.02, -0.14),
    kickRotationX: 0.35,
    kickRecoverySpeed: 7,
  },
};

const WEAPON_LIST: WeaponDef[] = Object.values(WEAPON_DEFS);

interface WeaponModelProps {
  def: WeaponDef;
  active: boolean;
  isMoving: boolean;
  actionSeq: number;
}

/**
 * Instancia de un arma FPOV individual. Todas quedan montadas a la vez
 * (para que cambiar de arma sea instantáneo, sin re-cargar el .glb) pero
 * solo la activa es `visible` -- así "solo se renderiza el arma activa" sin
 * pagar el costo de reparsear/clonar la escena en cada switch.
 */
function WeaponModel({ def, active, isMoving, actionSeq }: WeaponModelProps) {
  const { scene } = useGLTF(def.modelUrl);
  // Los rigs "with_arms"/"with_gloves" son SkinnedMesh -- `scene.clone(true)`
  // (Object3D.clone nativo) NO re-liga el skeleton a los huesos clonados, así
  // que el modelo queda con una pose degenerada e invisible aunque su
  // posición/material midan perfecto. SkeletonUtils.clone hace el rebind
  // correcto (ver three.js SkeletonUtils, el fix estándar para este caso).
  const clonedScene = useMemo(() => SkeletonUtils.clone(scene) as THREE.Object3D, [scene]);
  // El origen local del rig no coincide con el centro visual del modelo (el
  // rig trae un offset grande heredado del export, y a veces una malla
  // suelta casi sin volumen cerca del origen) -- sin recentrarlo, al rotar
  // el arma 180° ese offset termina detrás de la cámara y el arma
  // desaparece o se ve diminuta. Centramos el bounding box "significativo"
  // (ver computeSignificantBoundingBox) en el origen antes de escalar.
  const recenterOffset = useMemo(() => {
    const box = computeSignificantBoundingBox(clonedScene);
    return box.getCenter(new THREE.Vector3()).multiplyScalar(-1);
  }, [clonedScene]);
  const group = useRef<THREE.Group>(null!);
  const kick = useRef(0);
  const swayTime = useRef(0);
  const lastActionSeq = useRef(actionSeq);

  useEffect(() => {
    if (actionSeq !== lastActionSeq.current) {
      lastActionSeq.current = actionSeq;
      // Si el click llegó mientras esta arma no estaba en mano, no le
      // pegamos el kick -- solo queda sincronizado para no dispararlo tarde
      // al cambiar de arma después.
      if (active) kick.current = 1;
    }
  }, [actionSeq, active]);

  useFrame((_, delta) => {
    const swaySpeedNow = isMoving ? def.swaySpeed : def.swaySpeed * 0.3;
    const swayScale = isMoving ? 1 : 0.3;
    swayTime.current += delta * swaySpeedNow;

    const swayX = Math.sin(swayTime.current) * def.swayAmount * swayScale;
    const swayY = Math.abs(Math.cos(swayTime.current * 2)) * def.swayAmount * 0.6 * swayScale;

    // `THREE.MathUtils.lerp` no clampea su factor: un frame con `delta`
    // grande (tab en background, stall de GPU, hitch al cargar un .glb)
    // produce un factor > 1 que SOBREPASA el destino en vez de acercarse, y
    // ese overshoot compone frame a frame hasta divergir a valores
    // absurdos. Clampeamos cada factor a [0,1] antes de interpolar.
    const posLerpT = Math.min(delta * FOLLOW_SPEED, 1);
    const kickLerpT = Math.min(delta * (FOLLOW_SPEED + 4), 1);
    const kickRecoverT = Math.min(delta * def.kickRecoverySpeed, 1);

    kick.current = THREE.MathUtils.lerp(kick.current, 0, kickRecoverT);

    const target = group.current.position;
    target.x = THREE.MathUtils.lerp(target.x, def.basePosition.x + swayX + kick.current * def.kickPosition.x, posLerpT);
    target.y = THREE.MathUtils.lerp(target.y, def.basePosition.y + swayY + kick.current * def.kickPosition.y, posLerpT);
    target.z = THREE.MathUtils.lerp(target.z, def.basePosition.z + kick.current * def.kickPosition.z, kickLerpT);

    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, kick.current * def.kickRotationX, kickLerpT);
  });

  return (
    <group ref={group} visible={active} position={def.basePosition} rotation={[0, def.rotationY, 0]}>
      <group position={[recenterOffset.x * def.scale, recenterOffset.y * def.scale, recenterOffset.z * def.scale]}>
        <primitive object={clonedScene} scale={def.scale} />
      </group>
    </group>
  );
}

interface WeaponPOVProps {
  activeWeaponId: WeaponId;
  /** El jugador se está desplazando (WASD activo) -- intensifica el sway. */
  isMoving: boolean;
  /** Se incrementa en cada click -- dispara el kick (recoil o tajo) del arma activa. */
  actionSeq: number;
}

export function WeaponPOV({ activeWeaponId, isMoving, actionSeq }: WeaponPOVProps) {
  const { camera, scene: threeScene } = useThree();
  const rig = useRef<THREE.Group>(null!);

  // Las armas cuelgan de la cámara, no de la escena: así el sway/recoil son
  // offsets locales y siguen el look del mouse gratis. La cámara default de
  // R3F no es hija de la escena (Canvas la crea aparte), así que sin este
  // `scene.add(camera)` nada colgado de ella llega a dibujarse.
  useEffect(() => {
    const rigGroup = rig.current;
    if (camera.parent !== threeScene) threeScene.add(camera);
    camera.add(rigGroup);
    return () => {
      camera.remove(rigGroup);
    };
  }, [camera, threeScene]);

  return (
    <group ref={rig}>
      {WEAPON_LIST.map((def) => (
        <WeaponModel key={def.id} def={def} active={activeWeaponId === def.id} isMoving={isMoving} actionSeq={actionSeq} />
      ))}
    </group>
  );
}

for (const def of WEAPON_LIST) useGLTF.preload(def.modelUrl);
