import { useEffect, useMemo, useRef } from "react";
import { Html, useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { CapsuleCollider, RigidBody, type RapierRigidBody } from "@react-three/rapier";
import * as THREE from "three";
import { SkeletonUtils } from "three-stdlib";
import type { PrefireSpot } from "../../data/miragePrefireSpots";

export const TARGET_BOT_MODEL_URL = "/prefireaim/sas__cs2_agent_model_blue.glb";

interface TargetBotProps {
  spot: PrefireSpot;
  /** Se incrementa cada vez que el bot recibe un impacto -- dispara el feedback visual. */
  impactSeq: number;
  /** Click izquierdo mientras el puntero está bloqueado: R3F fuerza el raycast al centro de pantalla. */
  onHit: () => void;
}

const UP_QUATERNION = new THREE.Quaternion();
const EULER = new THREE.Euler();

/**
 * Bot objetivo del prefire trainer. Es "kinematicPosition" porque no debe
 * reaccionar a la física del mundo (no cae, no lo empuja el jugador) pero sí
 * debe bloquear raycasts/colisiones como un obstáculo sólido en su spot.
 */
export function TargetBot({ spot, impactSeq, onHit }: TargetBotProps) {
  const { scene } = useGLTF(TARGET_BOT_MODEL_URL);
  // El agente es un SkinnedMesh rigged -- `scene.clone(true)` no re-liga el
  // skeleton a los huesos clonados y el modelo queda invisible (mismo bug
  // que WeaponPOV.tsx). SkeletonUtils.clone hace el rebind correcto.
  const clonedScene = useMemo(() => SkeletonUtils.clone(scene) as THREE.Object3D, [scene]);
  const rigidBody = useRef<RapierRigidBody>(null);
  const modelGroup = useRef<THREE.Group>(null);
  const impactPulse = useRef(0);

  useEffect(() => {
    const body = rigidBody.current;
    if (!body) return;
    const [x, y, z] = spot.position;
    body.setNextKinematicTranslation({ x, y, z });
    EULER.set(0, spot.rotationY, 0);
    UP_QUATERNION.setFromEuler(EULER);
    body.setNextKinematicRotation(UP_QUATERNION);
  }, [spot]);

  useEffect(() => {
    if (impactSeq > 0) impactPulse.current = 1;
  }, [impactSeq]);

  useFrame((_, delta) => {
    if (!modelGroup.current) return;
    // Desintegración corta: el bot se "achica" y se recupera al instante
    // siguiente, simulando el impacto antes de reaparecer en el próximo spot.
    if (impactPulse.current > 0) {
      impactPulse.current = Math.max(0, impactPulse.current - delta * 6);
      const scale = 1 - impactPulse.current * 0.85;
      modelGroup.current.scale.setScalar(THREE.MathUtils.clamp(scale, 0.15, 1));
    } else {
      modelGroup.current.scale.setScalar(1);
    }
  });

  return (
    <RigidBody
      ref={rigidBody}
      type="kinematicPosition"
      colliders={false}
      position={spot.position}
      rotation={[0, spot.rotationY, 0]}
    >
      <CapsuleCollider args={[0.9, 0.4]} />
      <group
        ref={modelGroup}
        name={`target-bot-${spot.id}`}
        onPointerDown={(event) => {
          event.stopPropagation();
          onHit();
        }}
      >
        <primitive object={clonedScene} />
        <Html position={[0, 2.05, 0]} center distanceFactor={9} zIndexRange={[10, 0]}>
          <div className="prefire-bot-tag">{spot.callout}</div>
        </Html>
      </group>
    </RigidBody>
  );
}

useGLTF.preload(TARGET_BOT_MODEL_URL);
