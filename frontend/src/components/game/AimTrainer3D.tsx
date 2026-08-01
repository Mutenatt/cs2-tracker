import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, PointerLockControls, useGLTF } from "@react-three/drei";
import { CapsuleCollider, Physics, RigidBody, type RapierRigidBody } from "@react-three/rapier";
import * as THREE from "three";
import {
  MIRAGE_PREFIRE_ROUTINES,
  type PrefireRoutine,
  type Vec3,
} from "../../data/miragePrefireSpots";
import { findGroundY, snapRoutineToGround } from "./groundSnap";
import { MapModel, MIRAGE_MODEL_URL } from "./MapModel";
import { TargetBot } from "./TargetBot";
import { WEAPON_DEFS, WeaponPOV, type WeaponId } from "./WeaponPOV";

const WEAPON_HOTKEYS: Record<string, WeaponId> = {
  Digit1: "ak47",
  Digit3: "karambit",
};

// Mientras el puntero está bloqueado (jugando), el navegador entrega TODOS
// los clicks al elemento que pidió el lock, no al botón del HUD que esté
// visualmente encima -- es el comportamiento estándar de la Pointer Lock
// API, no algo que podamos parchear con z-index. Por eso el selector de
// rutina también necesita atajos de teclado, igual que ya tiene el arma.
const ROUTINE_HOTKEYS: Record<string, string> = {
  F1: "a-site",
  F2: "mid",
  F3: "b-site",
};
const ROUTINE_HOTKEY_LABELS: Record<string, string> = {
  "a-site": "F1",
  mid: "F2",
  "b-site": "F3",
};

/** Estado de inventario del jugador -- por ahora solo qué arma FPOV está activa. */
function useInventory(enabled: boolean) {
  const [activeWeaponId, setActiveWeaponId] = useState<WeaponId>("ak47");

  useEffect(() => {
    if (!enabled) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const weaponId = WEAPON_HOTKEYS[event.code];
      if (weaponId) setActiveWeaponId(weaponId);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled]);

  return { activeWeaponId, setActiveWeaponId };
}

const MOVE_SPEED = 6.5;
// Radio un poco más grande que el mínimo para dejar margen contra columnas
// o paredes finas -- con 0.35 la cámara (que está en el centro del
// collider) puede terminar visualmente metida en la malla cerca de
// esquinas, aunque el cuerpo físico ya esté "afuera".
const PLAYER_COLLIDER_ARGS: [number, number] = [0.55, 0.45];
// Altura de ojos parada, siguiendo la misma convención que ya usan los
// spawns "de piso" en miragePrefireSpots.ts (ver groundSnap.ts).
const EYE_HEIGHT = 1.6;
// Margen del raycast de piso por encima de la altura ACTUAL del jugador
// (no del techo de todo el mapa). Suficiente para detectar un escalón o
// rampa hacia arriba, pero sin "ver a través" de un techo de otro piso --
// eso era lo que dejaba al jugador enterrado en geometría al caminar bajo
// una estructura con techo.
const PLAYER_GROUND_RAY_MARGIN = 1.0;
// Velocidad máxima (unidades/seg) a la que la cámara puede subir/bajar para
// alcanzar el piso detectado. Sin este límite, `body.setTranslation`
// "teletransporta" instantáneamente al jugador al piso encontrado -- si
// camina hasta el borde de una plataforma/techo y el siguiente apoyo real
// está varios metros más abajo, aterriza de un salto ahí mismo, sin que el
// solver de colisión de Rapier tenga chance de resolver un posible
// solapamiento con paredes de esa zona (por eso quedaba "enterrado" y
// bloqueado). Subir es casi instantáneo (escalones/rampas); bajar es una
// caída gradual, no un salto.
const MAX_STEP_UP_SPEED = 8;
const MAX_FALL_SPEED = 14;

const KEY_TO_AXIS: Record<string, keyof MoveState> = {
  KeyW: "forward",
  ArrowUp: "forward",
  KeyS: "backward",
  ArrowDown: "backward",
  KeyA: "left",
  ArrowLeft: "left",
  KeyD: "right",
  ArrowRight: "right",
};

interface MoveState {
  forward: boolean;
  backward: boolean;
  left: boolean;
  right: boolean;
}

function useKeyboardMove(enabled: boolean) {
  const state = useRef<MoveState>({ forward: false, backward: false, left: false, right: false });

  useEffect(() => {
    if (!enabled) {
      state.current = { forward: false, backward: false, left: false, right: false };
      return;
    }
    const onKeyDown = (e: KeyboardEvent) => {
      const axis = KEY_TO_AXIS[e.code];
      if (axis) state.current[axis] = true;
    };
    const onKeyUp = (e: KeyboardEvent) => {
      const axis = KEY_TO_AXIS[e.code];
      if (axis) state.current[axis] = false;
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [enabled]);

  return state;
}

interface PlayerRigProps {
  spawn: Vec3;
  spawnRotationY: number;
  spawnToken: number;
  locked: boolean;
  mapScene: THREE.Object3D;
  onMovingChange: (moving: boolean) => void;
}

/**
 * Cuerpo físico invisible del jugador. Es "dynamic" para que el trimesh del
 * mapa lo frene en paredes/props, pero sin gravedad: el Y lo resolvemos
 * nosotros con un raycast al piso cada frame (ver groundSnap.ts). Confiar en
 * la gravedad de Rapier para "asentarlo" es lo que originalmente lo hacía
 * caer al vacío -- el trimesh de 2400+ mallas tarda un poco en construirse
 * y el body dinámico ya venía cayendo antes de que el collider existiera.
 */
function PlayerRig({ spawn, spawnRotationY, spawnToken, locked, mapScene, onMovingChange }: PlayerRigProps) {
  const { camera } = useThree();
  const rigidBody = useRef<RapierRigidBody>(null);
  const moveState = useKeyboardMove(locked);
  const wasMoving = useRef(false);
  const forwardVec = useMemo(() => new THREE.Vector3(), []);
  const rightVec = useMemo(() => new THREE.Vector3(), []);
  const moveVec = useMemo(() => new THREE.Vector3(), []);

  useEffect(() => {
    const body = rigidBody.current;
    if (!body) return;
    body.setTranslation({ x: spawn[0], y: spawn[1], z: spawn[2] }, true);
    body.setLinvel({ x: 0, y: 0, z: 0 }, true);
    camera.position.set(spawn[0], spawn[1], spawn[2]);
    camera.rotation.set(0, spawnRotationY, 0);
    // spawnToken es la única dependencia real: nos avisa "reposicionar ya".
  }, [spawnToken]);

  useFrame((_, delta) => {
    const body = rigidBody.current;
    if (!body) return;

    const { forward, backward, left, right } = moveState.current;
    const isMoving = forward || backward || left || right;
    if (isMoving !== wasMoving.current) {
      wasMoving.current = isMoving;
      onMovingChange(isMoving);
    }

    forwardVec.set(0, 0, -1).applyQuaternion(camera.quaternion);
    forwardVec.y = 0;
    forwardVec.normalize();
    rightVec.set(1, 0, 0).applyQuaternion(camera.quaternion);
    rightVec.y = 0;
    rightVec.normalize();

    moveVec.set(0, 0, 0);
    if (forward) moveVec.add(forwardVec);
    if (backward) moveVec.sub(forwardVec);
    if (right) moveVec.add(rightVec);
    if (left) moveVec.sub(rightVec);
    if (moveVec.lengthSq() > 0) moveVec.normalize().multiplyScalar(MOVE_SPEED);

    body.setLinvel({ x: moveVec.x, y: 0, z: moveVec.z }, true);

    const translation = body.translation();
    // El rayo arranca cerca de la altura actual del jugador, no del techo
    // de todo el mapa -- así nunca "ve a través" de un techo que tenga por
    // encima y siempre pisa el piso que tiene debajo de verdad.
    const groundY = findGroundY(
      mapScene,
      translation.x,
      translation.z,
      translation.y + PLAYER_GROUND_RAY_MARGIN,
      translation.y - EYE_HEIGHT,
    );
    const targetEyeY = groundY + EYE_HEIGHT;
    // Clampear cuánto puede subir/bajar la cámara en este frame -- sin esto,
    // `setTranslation` salta instantáneamente al piso encontrado, y si el
    // jugador camina fuera del borde de una plataforma y el siguiente apoyo
    // real está varios metros más abajo, aterriza de un salto ahí mismo sin
    // que el solver de colisión llegue a resolver un posible solapamiento
    // con paredes de esa zona.
    const maxStep = (targetEyeY >= translation.y ? MAX_STEP_UP_SPEED : MAX_FALL_SPEED) * delta;
    const eyeY = translation.y + THREE.MathUtils.clamp(targetEyeY - translation.y, -maxStep, maxStep);
    body.setTranslation({ x: translation.x, y: eyeY, z: translation.z }, true);
    camera.position.set(translation.x, eyeY, translation.z);
  });

  return (
    <RigidBody
      ref={rigidBody}
      type="dynamic"
      colliders={false}
      position={spawn}
      gravityScale={0}
      enabledRotations={[false, false, false]}
      linearDamping={0.5}
    >
      <CapsuleCollider args={PLAYER_COLLIDER_ARGS} />
    </RigidBody>
  );
}

interface GroundedGameplayProps {
  activeRoutine: PrefireRoutine;
  spotIndex: number;
  impactSeq: number;
  onHit: () => void;
  spawnToken: number;
  locked: boolean;
  onMovingChange: (moving: boolean) => void;
}

/**
 * Carga el mapa y usa su geometría real (ya con los node-transforms del
 * GLTF aplicados) para clavar al piso el spawn del jugador y cada spot de
 * la rutina activa -- ver groundSnap.ts para el porqué.
 */
function GroundedGameplay({
  activeRoutine,
  spotIndex,
  impactSeq,
  onHit,
  spawnToken,
  locked,
  onMovingChange,
}: GroundedGameplayProps) {
  const { scene } = useGLTF(MIRAGE_MODEL_URL);
  const groundedRoutine = useMemo(
    () => snapRoutineToGround(activeRoutine, scene, EYE_HEIGHT),
    [activeRoutine, scene],
  );
  const currentSpot = groundedRoutine.spots[spotIndex % groundedRoutine.spots.length];

  return (
    <>
      <MapModel />
      <TargetBot spot={currentSpot} impactSeq={impactSeq} onHit={onHit} />
      <PlayerRig
        spawn={groundedRoutine.playerSpawn}
        spawnRotationY={groundedRoutine.playerSpawnRotationY}
        spawnToken={spawnToken}
        locked={locked}
        mapScene={scene}
        onMovingChange={onMovingChange}
      />
    </>
  );
}

function Crosshair() {
  return (
    <div className="prefire-crosshair" aria-hidden>
      <span className="prefire-crosshair-line prefire-crosshair-h" />
      <span className="prefire-crosshair-line prefire-crosshair-v" />
      <span className="prefire-crosshair-dot" />
    </div>
  );
}

interface HudProps {
  routines: PrefireRoutine[];
  activeRoutineId: string;
  onSelectRoutine: (id: string) => void;
  score: number;
  currentCallout: string | undefined;
  locked: boolean;
  activeWeaponId: WeaponId;
  onSelectWeapon: (id: WeaponId) => void;
}

function Hud({
  routines,
  activeRoutineId,
  onSelectRoutine,
  score,
  currentCallout,
  locked,
  activeWeaponId,
  onSelectWeapon,
}: HudProps) {
  return (
    <div className="prefire-hud">
      <div className="prefire-hud-top">
        <div className="prefire-routine-select" role="tablist" aria-label="Rutina de prefire">
          {routines.map((routine) => (
            <button
              key={routine.id}
              type="button"
              role="tab"
              aria-selected={routine.id === activeRoutineId}
              className={`prefire-routine-btn${routine.id === activeRoutineId ? " active" : ""}`}
              onClick={() => onSelectRoutine(routine.id)}
            >
              {routine.label}
              <span className="prefire-routine-key">{ROUTINE_HOTKEY_LABELS[routine.id]}</span>
            </button>
          ))}
        </div>
        <div className="prefire-score-panel">
          <span className="prefire-score-label">Score</span>
          <span className="prefire-score-value">{score}</span>
        </div>
      </div>

      {currentCallout && <div className="prefire-target-callout">Target: {currentCallout}</div>}

      <div className="prefire-weapon-select" role="tablist" aria-label="Arma activa">
        {Object.values(WEAPON_DEFS).map((def) => (
          <button
            key={def.id}
            type="button"
            role="tab"
            aria-selected={def.id === activeWeaponId}
            className={`prefire-weapon-btn${def.id === activeWeaponId ? " active" : ""}`}
            onClick={() => onSelectWeapon(def.id)}
          >
            <span className="prefire-weapon-icon">{def.hudIcon}</span>
            <span className="prefire-weapon-label">{def.label}</span>
            <span className="prefire-weapon-key">{def.hotkeyLabel}</span>
          </button>
        ))}
      </div>

      {!locked && (
        <div className="prefire-lock-hint">
          <p>Click en la escena para entrar en primera persona</p>
          <p className="prefire-lock-hint-sub">
            WASD para moverte · Mouse para apuntar · Click para disparar
            <br />
            1/3 cambia de arma · F1/F2/F3 cambia de rutina (el mouse no sirve para los botones mientras jugás)
          </p>
        </div>
      )}
    </div>
  );
}

export function AimTrainer3D() {
  const [activeRoutineId, setActiveRoutineId] = useState(MIRAGE_PREFIRE_ROUTINES[0].id);
  const [spotIndex, setSpotIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [impactSeq, setImpactSeq] = useState(0);
  const [fireSeq, setFireSeq] = useState(0);
  const [isMoving, setIsMoving] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const spawnTokenRef = useRef(0);
  const [spawnToken, setSpawnToken] = useState(0);
  const lockedRef = useRef(false);
  const { activeWeaponId, setActiveWeaponId } = useInventory(isLocked);

  const activeRoutine = useMemo(
    () => MIRAGE_PREFIRE_ROUTINES.find((routine) => routine.id === activeRoutineId) ?? MIRAGE_PREFIRE_ROUTINES[0],
    [activeRoutineId],
  );
  const currentSpot = activeRoutine.spots[spotIndex % activeRoutine.spots.length];

  const handleSelectRoutine = (id: string) => {
    setActiveRoutineId(id);
    setScore(0);
    setSpotIndex(0);
    spawnTokenRef.current += 1;
    setSpawnToken(spawnTokenRef.current);
  };

  const handleHit = () => {
    setScore((s) => s + 100);
    setImpactSeq((n) => n + 1);
    setSpotIndex((i) => (i + 1) % activeRoutine.spots.length);
  };

  useEffect(() => {
    lockedRef.current = isLocked;
  }, [isLocked]);

  // Atajo de teclado para cambiar de rutina sin mouse -- necesario porque,
  // con el puntero bloqueado, los clicks en los botones del HUD nunca
  // llegan a React (ver comentario en ROUTINE_HOTKEYS).
  useEffect(() => {
    if (!isLocked) return;
    const onKeyDown = (event: KeyboardEvent) => {
      const routineId = ROUTINE_HOTKEYS[event.code];
      if (routineId) {
        event.preventDefault();
        handleSelectRoutine(routineId);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isLocked]);

  // El arma activa debe patear en cada click (impacte o no), así que el
  // fire-rate se escucha a nivel documento en vez de depender del handler
  // del bot.
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0 || !lockedRef.current) return;
      setFireSeq((n) => n + 1);
    };
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, []);

  return (
    <div className="prefire-trainer">
      <Canvas
        id="prefire-canvas-root"
        shadows
        camera={{ fov: 90, near: 0.05, far: 300 }}
        gl={{ antialias: true }}
      >
        <ambientLight intensity={0.55} />
        <directionalLight position={[40, 60, 20]} intensity={1.15} castShadow />
        <Suspense fallback={<Html center className="prefire-loading">Cargando Mirage…</Html>}>
          <Physics gravity={[0, -9.81, 0]}>
            <GroundedGameplay
              activeRoutine={activeRoutine}
              spotIndex={spotIndex}
              impactSeq={impactSeq}
              onHit={handleHit}
              spawnToken={spawnToken}
              locked={isLocked}
              onMovingChange={setIsMoving}
            />
          </Physics>
          <WeaponPOV activeWeaponId={activeWeaponId} isMoving={isMoving} actionSeq={fireSeq} />
        </Suspense>
        <PointerLockControls
          selector="#prefire-canvas-root"
          onLock={() => setIsLocked(true)}
          onUnlock={() => setIsLocked(false)}
        />
      </Canvas>

      <Crosshair />
      <Hud
        routines={MIRAGE_PREFIRE_ROUTINES}
        activeRoutineId={activeRoutineId}
        onSelectRoutine={handleSelectRoutine}
        score={score}
        currentCallout={currentSpot?.callout}
        locked={isLocked}
        activeWeaponId={activeWeaponId}
        onSelectWeapon={setActiveWeaponId}
      />
    </div>
  );
}
