import { useGLTF } from "@react-three/drei";
import { MeshCollider, RigidBody } from "@react-three/rapier";

export const MIRAGE_MODEL_URL = "/prefireaim/mirage_cs2_fps.glb";

/**
 * Mapa estático de Mirage. El trimesh collider replica la geometría visual
 * 1:1 -- correcto para paredes/piso porque el body es "fixed" y nunca se
 * mueve (Rapier solo prohíbe trimesh en bodies dinámicos).
 */
export function MapModel() {
  const { scene } = useGLTF(MIRAGE_MODEL_URL);

  return (
    <RigidBody type="fixed" colliders={false} friction={0.9}>
      <MeshCollider type="trimesh">
        <primitive object={scene} />
      </MeshCollider>
    </RigidBody>
  );
}

useGLTF.preload(MIRAGE_MODEL_URL);
