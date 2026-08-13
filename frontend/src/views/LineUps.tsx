import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { SectionLabel } from "../components/SectionLabel";
import { Topbar } from "../components/Topbar";
import { cardRise, staggerList } from "../components/motion/presets";
import { SmoothScroll } from "../components/motion/SmoothScroll";
import { LineupMapStage } from "../components/lineups/LineupMapStage";
import { LineupVideoModal } from "../components/lineups/LineupVideoModal";
import { LineupCoordEditor } from "../components/lineups/LineupCoordEditor";
import type { MapPin } from "../components/lineups/types";
import { getLineups } from "../api";
import type { LineupOut } from "../types";

type Side = "T" | "CT";
type Category = "smoke" | "flash" | "molotov" | "he";

interface MapEntry {
  key: string;
  name: string;
}

// Mismo pool de radares que ya viven en frontend/public/radar -- se reusan
// los iconos locales (sin depender de un CDN externo, a diferencia del
// mapIconUrl de HomeView).
const MAP_POOL: MapEntry[] = [
  { key: "de_ancient", name: "Ancient" },
  { key: "de_anubis", name: "Anubis" },
  { key: "de_cache", name: "Cache" },
  { key: "de_dust2", name: "Dust II" },
  { key: "de_inferno", name: "Inferno" },
  { key: "de_mirage", name: "Mirage" },
  { key: "de_nuke", name: "Nuke" },
];

const CATEGORY_LABEL: Record<Category, string> = {
  smoke: "Humo",
  flash: "Flash",
  molotov: "Molotov",
  he: "Granada HE",
};

const UTILITY_EFFECT_DURATION: Record<Category, number> = {
  smoke: 1100,
  flash: 1000,
  molotov: 1400,
  he: 820,
};

const MAP_BACKGROUND_BY_MAP: Record<string, string> = {
  de_ancient: "/fondo-lineups/ancient-fondo-lineup.jpg",
  de_anubis: "/fondo-lineups/anubis-fondo-lineup.jpg",
  de_cache: "/fondo-lineups/cache-fondo-lineup.jpeg",
  de_dust2: "/fondo-lineups/dust2-fondo-lineup.jpg",
  de_mirage: "/fondo-lineups/mirage-fondo-lineup.jpg",
  de_nuke: "/fondo-lineups/nuke-fondo-lineup.jpg",
  de_inferno: "/fondo-lineups/inferno-fondo-lineups.jpg",
};

// Los datos de lineups (posiciones y video_url ya presignado desde R2) salen
// de GET /lineups -- ver backend/cs2tracker/api/lineups.py y el seed en
// backend/scripts/seed_lineups.py (fuente de verdad del contenido).
function lineupsFor(
  rows: LineupOut[],
  category: Category | "all",
  side: Side
): LineupOut[] {
  return rows
    .filter((r) => category === "all" || r.category === category)
    .filter((r) => r.team == null || r.team === side);
}

// Preferencia de bajo consumo (pensada para RAM limitada): apaga los videos
// de fondo de las tarjetas de mapa. Se guarda en localStorage porque es una
// preferencia de la máquina/navegador, no de la cuenta.
const BG_ANIMATIONS_KEY = "cstats:lineups-bg-animations";

function loadBgAnimationsPref(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(BG_ANIMATIONS_KEY) !== "off";
}

// Para clips cuyo loop nativo (<video loop>) deja un corte visible una
// vez por vuelta (el contenido cambia de forma de golpe al reiniciar),
// se usan DOS copias del mismo clip desfasadas medio período: mientras
// una pasa por su propio corte (currentTime ~0 o ~fin), la otra está a
// mitad de camino, lejos del suyo, así que un crossfade por
// distancia-al-corte (calculado por rAF sobre el currentTime real de
// cada video, no en tiempo de reloj/CSS) siempre deja una copia
// totalmente opaca tapando el salto de la otra.
function CrossfadeLoopVideo({
  src,
  duration,
  crossfadeWindow,
  wrapperClassName,
  videoClassName,
}: {
  src: string;
  duration: number;
  crossfadeWindow: number;
  wrapperClassName?: string;
  videoClassName?: string;
}) {
  const videoARef = useRef<HTMLVideoElement>(null);
  const videoBRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const videoA = videoARef.current;
    const videoB = videoBRef.current;
    if (!videoA || !videoB) return;

    const offsetB = () => {
      videoB.currentTime = duration / 2;
    };
    if (videoB.readyState >= 1) {
      offsetB();
    } else {
      videoB.addEventListener("loadedmetadata", offsetB, { once: true });
    }

    const opacityFor = (currentTime: number) => {
      const distanceToSeam = Math.min(currentTime, duration - currentTime);
      return Math.min(1, distanceToSeam / crossfadeWindow);
    };

    let frame: number;
    const tick = () => {
      videoA.style.opacity = String(opacityFor(videoA.currentTime));
      videoB.style.opacity = String(opacityFor(videoB.currentTime));
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame);
      videoB.removeEventListener("loadedmetadata", offsetB);
    };
  }, [duration, crossfadeWindow]);

  return (
    <span className={wrapperClassName}>
      <video ref={videoARef} className={videoClassName} src={src} autoPlay loop muted playsInline />
      <video ref={videoBRef} className={videoClassName} src={src} autoPlay loop muted playsInline />
    </span>
  );
}

// fuego-molotov-loop.mp4 (2.375s) es la meseta "zoomeada" recortada del
// video original.
const MOLOTOV_LOOP_DURATION = 2.375;
const MOLOTOV_CROSSFADE_WINDOW = 0.18;

function MolotovFireVideo() {
  return (
    <CrossfadeLoopVideo
      src="/media/fuego-molotov-loop.mp4"
      duration={MOLOTOV_LOOP_DURATION}
      crossfadeWindow={MOLOTOV_CROSSFADE_WINDOW}
      wrapperClassName="lineup-molotov-fire-stack"
      videoClassName="lineup-molotov-fire"
    />
  );
}

// mirage-arena.mp4 (~5.04s) no tiene una meseta recortada como el
// molotov, así que el crossfade es lo único que disimula el corte del
// loop.
const MIRAGE_ARENA_DURATION = 5.041667;
const MIRAGE_ARENA_CROSSFADE_WINDOW = 0.35;

function MirageArenaVideo() {
  return (
    <CrossfadeLoopVideo
      src="/media/mirage-arena.mp4"
      duration={MIRAGE_ARENA_DURATION}
      crossfadeWindow={MIRAGE_ARENA_CROSSFADE_WINDOW}
      wrapperClassName="map-card-fx map-arena-crossfade"
    />
  );
}

// nuke-arena.mp4 (~5.875s) tampoco tiene una meseta recortada.
const NUKE_ARENA_DURATION = 5.875;
const NUKE_ARENA_CROSSFADE_WINDOW = 0.4;

function NukeArenaVideo() {
  return (
    <CrossfadeLoopVideo
      src="/media/nuke-arena.mp4"
      duration={NUKE_ARENA_DURATION}
      crossfadeWindow={NUKE_ARENA_CROSSFADE_WINDOW}
      wrapperClassName="map-card-fx map-arena-crossfade map-arena-nuke"
    />
  );
}

function MapArenaVideo({
  className,
  src,
  startAt,
}: {
  className?: string;
  src: string;
  startAt: number;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const seekToStart = () => {
      video.currentTime = startAt;
    };
    const restartLoop = () => {
      video.currentTime = startAt;
      video.play();
    };
    if (video.readyState >= 1) {
      seekToStart();
    } else {
      video.addEventListener("loadedmetadata", seekToStart, { once: true });
    }
    video.addEventListener("ended", restartLoop);

    return () => {
      video.removeEventListener("loadedmetadata", seekToStart);
      video.removeEventListener("ended", restartLoop);
    };
  }, [startAt]);

  return <video ref={videoRef} className={className} src={src} autoPlay muted playsInline />;
}

function SmokeExplosionVideo() {
  return (
    <span className="lineup-smoke-video-stack">
      <video
        className="lineup-smoke-video"
        src="/media/explosion-humo.mp4"
        autoPlay
        loop
        muted
        playsInline
      />
    </span>
  );
}

function UtilityButtonEffect({ category }: { category: Category }) {
  return (
    <span className={`lineup-filter-effect lineup-filter-effect-${category}`} aria-hidden="true">
      {category === "molotov" ? (
        <MolotovFireVideo />
      ) : category === "smoke" ? (
        <SmokeExplosionVideo />
      ) : category === "he" ? (
        <span className="lineup-he-stack">
          <img className="lineup-he-bg" src="/fondo-lineups/explosion-he.gif" alt="" />
        </span>
      ) : null}
    </span>
  );
}

export function LineUps({ onLogout }: { onLogout: () => void }) {
  const [activeMap, setActiveMap] = useState(
    MAP_POOL.find((m) => m.key === "de_mirage")?.key ?? MAP_POOL[0].key
  );
  const [displayedMap, setDisplayedMap] = useState(activeMap);
  const [nextMap, setNextMap] = useState<string | null>(null);
  const [isBackgroundTransitioning, setIsBackgroundTransitioning] = useState(false);
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");
  const [animatingCategory, setAnimatingCategory] = useState<Category | null>(null);
  const [animationTick, setAnimationTick] = useState(0);
  const [activeSide, setActiveSide] = useState<Side>("T");
  const [bgAnimationsOn, setBgAnimationsOn] = useState(loadBgAnimationsPref);
  const [hoveredPinId, setHoveredPinId] = useState<string | null>(null);
  const [selectedPin, setSelectedPin] = useState<MapPin | null>(null);
  const [editingCoords, setEditingCoords] = useState(false);
  // Overrides locales (no persisten a disco): "Ajustar posiciones" permite
  // arrastrar pines para previsualizar, pero no hay endpoint de escritura
  // todavía -- ver comentario en backend/cs2tracker/api/lineups.py.
  const [coordOverrides, setCoordOverrides] = useState<Record<string, { x: number; y: number }>>(
    {}
  );
  const [mapLineups, setMapLineups] = useState<LineupOut[]>([]);
  const [lineupsLoading, setLineupsLoading] = useState(true);

  useEffect(() => {
    window.localStorage.setItem(BG_ANIMATIONS_KEY, bgAnimationsOn ? "on" : "off");
  }, [bgAnimationsOn]);

  useEffect(() => {
    let cancelled = false;
    setLineupsLoading(true);
    getLineups(activeMap)
      .then((rows) => {
        if (!cancelled) setMapLineups(rows);
      })
      .catch((err) => {
        console.error("GET /lineups falló", err);
        if (!cancelled) setMapLineups([]);
      })
      .finally(() => {
        if (!cancelled) setLineupsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeMap]);

  // Filtrar mapa/categoría/lado deja pines viejos "colgados" en hover o
  // seleccionados si no se limpia el estado del mapa al cambiar el contexto.
  useEffect(() => {
    setHoveredPinId(null);
    setSelectedPin(null);
  }, [activeMap, activeCategory, activeSide]);

  useEffect(() => {
    if (activeMap === displayedMap) {
      setNextMap(null);
      setIsBackgroundTransitioning(false);
      return;
    }

    setNextMap(activeMap);
    setIsBackgroundTransitioning(true);
    const timer = window.setTimeout(() => {
      setDisplayedMap(activeMap);
      setNextMap(null);
      setIsBackgroundTransitioning(false);
    }, 320);

    return () => window.clearTimeout(timer);
  }, [activeMap, displayedMap]);

  useEffect(() => {
    if (!animatingCategory) return;

    const timer = window.setTimeout(() => {
      setAnimatingCategory(null);
    }, UTILITY_EFFECT_DURATION[animatingCategory]);

    return () => window.clearTimeout(timer);
  }, [animatingCategory, animationTick]);

  const mapName = MAP_POOL.find((m) => m.key === activeMap)?.name ?? activeMap;
  const items = useMemo(
    () => lineupsFor(mapLineups, activeCategory, activeSide),
    [mapLineups, activeCategory, activeSide]
  );
  const total = mapLineups.length;
  const mapPins: MapPin[] = useMemo(
    () =>
      items.map((row) => ({
        id: String(row.id),
        category: row.category,
        team: row.team ?? undefined,
        label: row.label,
        x: row.x,
        y: row.y,
        startX: row.start_x ?? undefined,
        startY: row.start_y ?? undefined,
        videoUrl: row.video_url,
        instructions: row.instructions ?? undefined,
        crosshairNote: row.crosshair_note ?? undefined,
      })),
    [items]
  );
  const displayedPins: MapPin[] = useMemo(
    () =>
      mapPins.map((pin) => (coordOverrides[pin.id] ? { ...pin, ...coordOverrides[pin.id] } : pin)),
    [mapPins, coordOverrides]
  );
  const handlePinDrag = (id: string, x: number, y: number) => {
    setCoordOverrides((prev) => ({ ...prev, [id]: { x, y } }));
  };
  const pageBackgroundStyle = {
    backgroundImage: `linear-gradient(120deg, rgba(6, 12, 20, 0.9) 0%, rgba(6, 12, 20, 0.56) 100%), url(${MAP_BACKGROUND_BY_MAP[displayedMap] ?? "/fondo-lineups/mirage-fondo-lineup.jpg"})`,
    backgroundColor: "#060c14",
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundRepeat: "no-repeat",
    backgroundAttachment: "fixed",
    opacity: isBackgroundTransitioning ? 0.2 : 1,
    transition: "opacity 320ms ease",
  } as const;

  const nextBackgroundStyle = {
    backgroundImage: `linear-gradient(120deg, rgba(6, 12, 20, 0.9) 0%, rgba(6, 12, 20, 0.56) 100%), url(${MAP_BACKGROUND_BY_MAP[nextMap ?? displayedMap] ?? "/fondo-lineups/mirage-fondo-lineup.jpg"})`,
    backgroundColor: "#060c14",
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundRepeat: "no-repeat",
    backgroundAttachment: "fixed",
    opacity: isBackgroundTransitioning ? 1 : 0,
    transition: "opacity 320ms ease",
  } as const;

  return (
    <SmoothScroll>
      <div className={`lineup-page-shell lineup-side-${activeSide.toLowerCase()}`}>
        <div
          className="lineup-page-backdrop lineup-page-backdrop-current"
          style={pageBackgroundStyle}
        />
        <div
          className="lineup-page-backdrop lineup-page-backdrop-next"
          style={nextBackgroundStyle}
        />
        <div className="lineup-page-content">
          <Topbar onLogout={onLogout} />

          <motion.div
            className="map-pool-grid"
            variants={staggerList}
            initial="hidden"
            animate="show"
          >
            {MAP_POOL.map((m) => (
              <motion.button
                key={m.key}
                type="button"
                className={`map-pool-card lineup-map-card map-effect-${m.key}${
                  m.key === activeMap ? " active" : ""
                }`}
                variants={cardRise}
                whileHover={{ y: -3, scale: 1.02 }}
                whileTap={{ scale: 0.99 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                onClick={() => {
                  setActiveMap(m.key);
                }}
              >
                {/* Efecto atmosférico específico del mapa -- sin renderizar el
                    <video> cuando bgAnimationsOn está apagado, así el navegador
                    no llega ni a decodificar el clip (no alcanza con pausarlo). */}
                {!bgAnimationsOn ? (
                  <span className="map-card-fx" aria-hidden="true" />
                ) : m.key === "de_ancient" ? (
                  <MapArenaVideo
                    className="map-card-fx"
                    src="/media/ancient-arena.mp4"
                    startAt={2}
                  />
                ) : m.key === "de_anubis" ? (
                  <MapArenaVideo
                    className="map-card-fx"
                    src="/media/anubis-arena.mp4"
                    startAt={2}
                  />
                ) : m.key === "de_dust2" ? (
                  <MapArenaVideo className="map-card-fx" src="/media/dust2-arena.mp4" startAt={2} />
                ) : m.key === "de_inferno" ? (
                  <MapArenaVideo
                    className="map-card-fx"
                    src="/media/inferno-arena.mp4"
                    startAt={2}
                  />
                ) : m.key === "de_mirage" ? (
                  <MirageArenaVideo />
                ) : m.key === "de_nuke" ? (
                  <NukeArenaVideo />
                ) : (
                  <span className="map-card-fx" aria-hidden="true" />
                )}

                {/* Contenido de la tarjeta */}
                <span className="map-card-content">
                  <img
                    className="map-pool-icon"
                    src={`/map-icons/${m.key}.png`}
                    alt={m.name}
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
                    }}
                  />

                  <span className="map-pool-name">{m.name}</span>
                </span>
              </motion.button>
            ))}
          </motion.div>

          <div className="lineup-perf-switch-row">
            <span className="lineup-perf-switch-label">Animaciones</span>
            <button
              type="button"
              role="switch"
              aria-checked={bgAnimationsOn}
              className={`lineup-perf-switch${bgAnimationsOn ? " on" : ""}`}
              onClick={() => setBgAnimationsOn((v) => !v)}
              title="Apagá los videos de fondo de los mapas si tu PC tiene poca RAM"
            />
          </div>

          <div className="section-head">
            <SectionLabel>{mapName}</SectionLabel>
            <span className="rule" />
          </div>

          <div className="lineup-side-toggle-wrap">
            <div className="lineup-side-slide-slot lineup-side-slide-slot-t">
              <AnimatePresence>
                {activeSide === "T" && (
                  <motion.img
                    key="t"
                    className="lineup-side-slide-img lineup-side-slide-img-t"
                    src="/fondo-lineups/c4-tt-v5.png"
                    alt=""
                    aria-hidden="true"
                    initial={{ x: -140, opacity: 0, rotate: -10 }}
                    animate={{ x: 0, opacity: 1, rotate: 0 }}
                    exit={{ x: -140, opacity: 0, rotate: -10 }}
                    transition={{ duration: 0.45, ease: "easeOut" }}
                  />
                )}
              </AnimatePresence>
            </div>
            <div className="lineup-side-slide-slot lineup-side-slide-slot-ct">
              <AnimatePresence>
                {activeSide === "CT" && (
                  <motion.img
                    key="ct"
                    className="lineup-side-slide-img lineup-side-slide-img-ct"
                    src="/fondo-lineups/defuse-ct-v2.png"
                    alt=""
                    aria-hidden="true"
                    initial={{ x: 140, opacity: 0, rotate: 10 }}
                    animate={{ x: 0, opacity: 1, rotate: 0 }}
                    exit={{ x: 140, opacity: 0, rotate: 10 }}
                    transition={{ duration: 0.45, ease: "easeOut" }}
                  />
                )}
              </AnimatePresence>
            </div>

            <div className="lineup-side-toggle">
              <button
                type="button"
                className={`lineup-side-btn${activeSide === "T" ? " active-t" : ""}`}
                onClick={() => setActiveSide("T")}
                aria-label="Granadas TT"
                aria-pressed={activeSide === "T"}
              >
                <img
                  className="lineup-side-btn-logo"
                  src="/fondo-lineups/logo-tt.jpg"
                  alt="Logo TT"
                />
              </button>
              <button
                type="button"
                className={`lineup-side-btn${activeSide === "CT" ? " active-ct" : ""}`}
                onClick={() => setActiveSide("CT")}
                aria-label="Granadas CT"
                aria-pressed={activeSide === "CT"}
              >
                <img
                  className="lineup-side-btn-logo"
                  src="/fondo-lineups/logo-ct.jpg"
                  alt="Logo CT"
                />
              </button>
            </div>
          </div>

          <div className="lineup-filters lineup-filters-category">
            <button
              type="button"
              className={`lineup-filter${activeCategory === "all" ? " active" : ""}`}
              onClick={() => setActiveCategory("all")}
            >
              Todas ({total})
            </button>
            {(Object.keys(CATEGORY_LABEL) as Category[]).map((c) => {
              const count = mapLineups.filter((i) => i.category === c).length;
              return (
                <button
                  key={c}
                  type="button"
                  className={`lineup-filter lineup-filter-utility-${c}${activeCategory === c ? " active" : ""}${animatingCategory === c ? ` lineup-filter-animate-${c}` : ""}`}
                  onClick={() => {
                    setActiveCategory(c);
                    setAnimatingCategory(c);
                    setAnimationTick((value) => value + 1);
                  }}
                >
                  <UtilityButtonEffect category={c} />
                  <span className="lineup-filter-label">
                    {CATEGORY_LABEL[c]} ({count})
                  </span>
                </button>
              );
            })}
          </div>

          {lineupsLoading ? null : items.length === 0 ? (
            <div className="lineup-empty">
              <span className="lineup-empty-title">
                Todavía no hay line ups guardados para {mapName}.
              </span>
              <span className="lineup-empty-sub">
                Sumá entradas en <code>backend/scripts/seed_lineups.py</code> y corré el seed para
                que aparezcan acá.
              </span>
            </div>
          ) : (
            <motion.div
              className="lineup-map-section"
              variants={staggerList}
              initial="hidden"
              animate="show"
              key={`${activeMap}:${activeCategory}:${activeSide}`}
            >
              <LineupCoordEditor
                pins={displayedPins}
                editing={editingCoords}
                onToggle={() => setEditingCoords((v) => !v)}
              />
              <motion.div variants={cardRise}>
                <LineupMapStage
                  mapKey={activeMap}
                  pins={displayedPins}
                  hoveredId={hoveredPinId}
                  onPinHoverStart={setHoveredPinId}
                  onPinHoverEnd={() => setHoveredPinId(null)}
                  onPinSelect={setSelectedPin}
                  editable={editingCoords}
                  onPinDrag={handlePinDrag}
                />
              </motion.div>
            </motion.div>
          )}
        </div>
      </div>

      {selectedPin && <LineupVideoModal pin={selectedPin} onClose={() => setSelectedPin(null)} />}
    </SmoothScroll>
  );
}
