// Porteado del handoff de Claude Design (public/logo/Medalla táctica 3D
// interactiva-handoff2.0/.../TacticalBadge3D.tsx) -- misma geometría (disco +
// relieve SVG extruido a dos caras + muescas de canto) y mismo bloom
// selectivo por capa, solo con imports/estilo ajustados a este repo.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { EffectComposer, SelectiveBloom, Vignette } from "@react-three/postprocessing";
import gsap from "gsap";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { SVGLoader } from "three/examples/jsm/loaders/SVGLoader.js";

const ACCENTS = {
  ice: { base: "#2f8fd8", hot: "#6fd0ff" },
  blood: { base: "#c81e1e", hot: "#ff4a3d" },
  tactical: { base: "#4a5d3a", hot: "#8fd15a" },
} as const;

export type AccentName = keyof typeof ACCENTS;

export interface TacticalBadge3DProps {
  accent?: AccentName;
  /** Velocidad de la rotación continua en Y, en rad/s. */
  spinSpeed?: number;
  background?: "gradient" | "transparent";
  frameloop?: "always" | "demand";
  className?: string;
  style?: CSSProperties;
}

const GUNMETAL = "#2a2d31";

const SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">';

const SVG_RETICLE =
  SVG_HEAD +
  '<path d="M 16.75 50 A 33.25 33.25 0 1 0 83.25 50 A 33.25 33.25 0 1 0 16.75 50 Z' +
  ' M 19.25 50 A 30.75 30.75 0 1 1 80.75 50 A 30.75 30.75 0 1 1 19.25 50 Z"/>' +
  '<rect x="47.6" y="4" width="4.8" height="12" rx="2.4"/>' +
  '<rect x="47.6" y="84" width="4.8" height="12" rx="2.4"/>' +
  '<rect x="4" y="47.6" width="12" height="4.8" rx="2.4"/>' +
  '<rect x="84" y="47.6" width="12" height="4.8" rx="2.4"/></svg>';

const SVG_BARS =
  SVG_HEAD +
  '<rect x="30.5" y="42" width="5" height="16" rx="2.5"/>' +
  '<rect x="39" y="37" width="5" height="26" rx="2.5"/>' +
  '<rect x="56" y="37" width="5" height="26" rx="2.5"/>' +
  '<rect x="64.5" y="42" width="5" height="16" rx="2.5"/></svg>';

const SVG_BAR_CORE = SVG_HEAD + '<rect x="47.5" y="33" width="5" height="34" rx="2.5"/></svg>';

const SVG_SCALE = 0.0156;

function extrudeSvg(svg: string, depth: number): THREE.ExtrudeGeometry {
  const loader = new SVGLoader();
  const shapes: THREE.Shape[] = [];
  for (const path of loader.parse(svg).paths) shapes.push(...SVGLoader.createShapes(path));
  const geo = new THREE.ExtrudeGeometry(shapes, {
    depth,
    bevelEnabled: true,
    bevelThickness: 0.7,
    bevelSize: 0.7,
    bevelSegments: 3,
    curveSegments: 24,
  });
  geo.translate(-50, -50, 0);
  geo.scale(SVG_SCALE, SVG_SCALE, SVG_SCALE);
  return geo;
}

const FRONT = 0.1; // z de la cara plana frontal del disco

interface BadgeProps {
  accent: AccentName;
  spinSpeed: number;
  onLights: (lights: THREE.Light[]) => void;
  onBloomTargets: (targets: THREE.Mesh[]) => void;
}

function Badge({ accent, spinSpeed, onLights, onBloomTargets }: BadgeProps) {
  const floatRef = useRef<THREE.Group>(null!);
  const spinRef = useRef<THREE.Group>(null!);
  const rimRef = useRef<THREE.DirectionalLight>(null!);
  const keyRef = useRef<THREE.DirectionalLight>(null!);
  const faceGroups = useRef<THREE.Group[]>([]);

  const palette = ACCENTS[accent];

  const geos = useMemo(() => {
    const shape = new THREE.Shape();
    shape.absarc(0, 0, 1, 0, Math.PI * 2, false);
    const disc = new THREE.ExtrudeGeometry(shape, {
      depth: 0.11,
      bevelEnabled: true,
      bevelThickness: 0.045,
      bevelSize: 0.055,
      bevelSegments: 8,
      curveSegments: 128,
    });
    disc.center();
    return {
      disc,
      plate: new THREE.CylinderGeometry(0.8, 0.8, 0.03, 96),
      bezel: new THREE.TorusGeometry(0.815, 0.026, 16, 128),
      accentRing: new THREE.TorusGeometry(0.905, 0.017, 16, 128),
      knurl: new THREE.BoxGeometry(0.05, 0.075, 0.2),
      reticle: extrudeSvg(SVG_RETICLE, 3.2),
      bars: extrudeSvg(SVG_BARS, 4.5),
      core: extrudeSvg(SVG_BAR_CORE, 5.2),
    };
  }, []);

  useEffect(() => () => Object.values(geos).forEach((g) => g.dispose()), [geos]);

  const knurls = useMemo(
    () =>
      Array.from({ length: 48 }, (_, i) => {
        const a = (i / 48) * Math.PI * 2;
        return { a, x: Math.cos(a) * 0.985, y: Math.sin(a) * 0.985 };
      }),
    [],
  );

  useLayoutEffect(() => {
    onLights([rimRef.current, keyRef.current].filter(Boolean));
    const glowing: THREE.Mesh[] = [];
    for (const g of faceGroups.current) {
      g?.traverse((o) => {
        if ((o as THREE.Mesh).isMesh && o.userData.bloom) glowing.push(o as THREE.Mesh);
      });
    }
    onBloomTargets(glowing);
  }, [onLights, onBloomTargets]);

  useEffect(() => {
    const tl = gsap.timeline({ repeat: -1, yoyo: true });
    tl.fromTo(
      floatRef.current.rotation,
      { x: -0.13 },
      { x: 0.13, duration: 3.4, ease: "sine.inOut" },
    ).fromTo(
      floatRef.current.position,
      { y: -0.05 },
      { y: 0.05, duration: 3.4, ease: "sine.inOut" },
      0,
    );
    return () => {
      tl.kill();
    };
  }, []);

  useFrame((_, delta) => {
    spinRef.current.rotation.y += spinSpeed * Math.min(delta, 0.05);
  });

  return (
    <group ref={floatRef} position={[0, 0.42, 0]}>
      <directionalLight ref={rimRef} color="#5ec8ff" intensity={4.2} position={[-2.2, 1.6, -3.6]} />
      <directionalLight ref={keyRef} color="#ffd7ac" intensity={1.5} position={[3, 3, 3]} />
      <directionalLight color="#9fb2c8" intensity={0.35} position={[-1.5, -2, 2]} />
      <ambientLight color="#30363d" intensity={0.6} />

      <group ref={spinRef}>
        <mesh name="disc" geometry={geos.disc}>
          <meshPhysicalMaterial
            name="gunmetal"
            color={GUNMETAL}
            metalness={1}
            roughness={0.25}
            clearcoat={0.6}
            clearcoatRoughness={0.1}
          />
        </mesh>

        {(["front", "back"] as const).map((side, i) => (
          <group
            key={side}
            name={`face_${side}`}
            ref={(g: THREE.Group) => {
              faceGroups.current[i] = g;
            }}
            rotation={[0, side === "back" ? Math.PI : 0, 0]}
          >
            <mesh
              name="innerPlate"
              geometry={geos.plate}
              rotation={[Math.PI / 2, 0, 0]}
              position={[0, 0, FRONT + 0.014]}
            >
              <meshPhysicalMaterial
                name="plate"
                color="#1b1e22"
                metalness={0.95}
                roughness={0.42}
                clearcoat={0.35}
                clearcoatRoughness={0.2}
              />
            </mesh>

            <mesh name="bezel" geometry={geos.bezel} position={[0, 0, FRONT + 0.016]}>
              <meshPhysicalMaterial
                name="steel"
                color="#c3c9d2"
                metalness={1}
                roughness={0.18}
                clearcoat={0.6}
                clearcoatRoughness={0.08}
              />
            </mesh>

            <mesh
              name="accentRing"
              geometry={geos.accentRing}
              position={[0, 0, FRONT - 0.006]}
              userData={{ bloom: true }}
            >
              <meshPhysicalMaterial
                name="accent"
                color={palette.base}
                metalness={0.9}
                roughness={0.28}
                clearcoat={0.6}
                clearcoatRoughness={0.1}
                emissive={palette.hot}
                emissiveIntensity={0.16}
              />
            </mesh>

            <mesh
              name="reticle"
              geometry={geos.reticle}
              position={[0, 0, FRONT + 0.026]}
              userData={{ bloom: true }}
            >
              <meshPhysicalMaterial
                name="accent"
                color={palette.base}
                metalness={0.9}
                roughness={0.28}
                clearcoat={0.6}
                clearcoatRoughness={0.1}
                emissive={palette.hot}
                emissiveIntensity={0.16}
              />
            </mesh>

            <mesh name="bars" geometry={geos.bars} position={[0, 0, FRONT + 0.026]}>
              <meshPhysicalMaterial
                name="steel"
                color="#c3c9d2"
                metalness={1}
                roughness={0.18}
                clearcoat={0.6}
                clearcoatRoughness={0.08}
              />
            </mesh>

            <mesh
              name="barCore"
              geometry={geos.core}
              position={[0, 0, FRONT + 0.026]}
              userData={{ bloom: true }}
            >
              <meshPhysicalMaterial
                name="accentHot"
                color={palette.hot}
                metalness={0.6}
                roughness={0.25}
                clearcoat={0.6}
                clearcoatRoughness={0.1}
                emissive={palette.hot}
                emissiveIntensity={0.55}
              />
            </mesh>
          </group>
        ))}

        {knurls.map(({ a, x, y }, i) => (
          <mesh key={i} name={`knurl_${i}`} geometry={geos.knurl} position={[x, y, 0]} rotation={[0, 0, a]}>
            <meshPhysicalMaterial
              name="gunmetal"
              color={GUNMETAL}
              metalness={1}
              roughness={0.25}
              clearcoat={0.6}
              clearcoatRoughness={0.1}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}

// drei's <Environment preset="..."> baja un HDRI de un CDN externo -- sin
// eso los materiales metalness=1 no tienen nada que reflejar y el disco sale
// negro salvo por los brillos puntuales de las luces direccionales. Un
// RoomEnvironment generado localmente (mismo truco que el prototipo vanilla
// en badge-hero.html) da el reflejo sin depender de red.
function ProceduralEnvironment() {
  const { gl, scene } = useThree();

  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
    scene.environment = envRT.texture;
    return () => {
      scene.environment = null;
      envRT.dispose();
      pmrem.dispose();
    };
  }, [gl, scene]);

  return null;
}

const FIT_RADIUS = 2.25;

function ResponsiveCamera() {
  const { camera, size } = useThree();

  useLayoutEffect(() => {
    const cam = camera as THREE.PerspectiveCamera;
    const aspect = size.width / size.height;
    const baseFov = size.width < 640 ? 42 : 35;
    const fov =
      aspect < 1
        ? THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(baseFov) / 2) / aspect))
        : baseFov;
    cam.fov = fov;
    cam.position.set(0, 0.42, FIT_RADIUS / Math.tan(THREE.MathUtils.degToRad(fov) / 2));
    cam.updateProjectionMatrix();
  }, [camera, size]);

  return null;
}

export default function TacticalBadge3D({
  accent = "ice",
  spinSpeed = 0.15,
  background = "gradient",
  frameloop = "always",
  className,
  style,
}: TacticalBadge3DProps) {
  const [lights, setLights] = useState<THREE.Light[]>([]);
  const [bloomTargets, setBloomTargets] = useState<THREE.Mesh[]>([]);

  return (
    <div
      className={className}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        background:
          background === "gradient"
            ? "radial-gradient(ellipse 70% 70% at 50% 45%, #1a1a1e 0%, #0a0a0c 70%)"
            : "transparent",
        ...style,
      }}
    >
      <Canvas
        frameloop={frameloop}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        camera={{ fov: 35, position: [0, 0.42, 4.9], near: 0.1, far: 100 }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.05;
        }}
      >
        <ResponsiveCamera />
        <ProceduralEnvironment />
        <Badge accent={accent} spinSpeed={spinSpeed} onLights={setLights} onBloomTargets={setBloomTargets} />

        {bloomTargets.length > 0 && (
          <EffectComposer enableNormalPass={false}>
            <SelectiveBloom
              lights={lights}
              selection={bloomTargets}
              selectionLayer={11}
              intensity={0.32}
              radius={0.22}
              luminanceThreshold={0.28}
              luminanceSmoothing={0.6}
              mipmapBlur
            />
            <Vignette offset={0.3} darkness={0.45} eskil={false} />
          </EffectComposer>
        )}
      </Canvas>
    </div>
  );
}
