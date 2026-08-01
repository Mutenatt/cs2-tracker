import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { SectionLabel } from "../components/SectionLabel";
import { Topbar } from "../components/Topbar";
import { cardRise, staggerList } from "../components/motion/presets";

type Side = "T" | "CT";
type Category = "smoke" | "flash" | "molotov" | "he";

interface MapEntry {
  key: string;
  name: string;
}

interface LineupItem {
  id: string;
  title: string;
  side: Side;
  category: Category;
  to: string;
  from?: string;
  video: string;
  notes?: string;
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

const CATEGORY_CLASS: Record<Category, string> = {
  smoke: "lineup-tag-smoke",
  flash: "lineup-tag-flash",
  molotov: "lineup-tag-molotov",
  he: "lineup-tag-he",
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

// Cada video vive en frontend/public/lineups/{mapa}/{ct|t}/archivo.mp4 (ver
// carpeta real en disco). Sumar un mapa nuevo es: 1) tirar los .mp4 en esa
// ruta, 2) agregar acá una entrada por video. Sin entradas, el mapa cae
// directo al estado vacío -- el "to" sale del nombre de archivo tal cual lo
// grabó el usuario, revisar/ajustar el callout si no coincide.
const LINEUPS: Record<string, LineupItem[]> = {
  de_mirage: [
    // ---- CT ----
    {
      id: "mirage-ct-deto-caverna",
      title: "Granada HE — Caverna",
      side: "CT",
      category: "he",
      to: "Caverna",
      video: "/lineups/de_mirage/ct/deto-ct-caverna.mp4",
    },
    {
      id: "mirage-ct-moli-caverna",
      title: "Molotov — Caverna",
      side: "CT",
      category: "molotov",
      to: "Caverna",
      video: "/lineups/de_mirage/ct/moli-ct-caverna.mp4",
    },
    {
      id: "mirage-ct-moli-tapete",
      title: "Molotov — Tapete",
      side: "CT",
      category: "molotov",
      to: "Tapete",
      video: "/lineups/de_mirage/ct/moli-ct-tapete.mp4",
    },
    {
      id: "mirage-ct-popflash-mid",
      title: "Popflash — Mid",
      side: "CT",
      category: "flash",
      to: "Mid",
      video: "/lineups/de_mirage/ct/popflash-cd-mid.mp4",
    },
    {
      id: "mirage-ct-popflash-medio",
      title: "Popflash — Medio",
      side: "CT",
      category: "flash",
      to: "Medio",
      video: "/lineups/de_mirage/ct/popflash-ct-medio.mp4",
    },
    {
      id: "mirage-ct-smoke-l",
      title: "Humo — Zona L",
      side: "CT",
      category: "smoke",
      to: "Zona L",
      video: "/lineups/de_mirage/ct/smoke-ct-L.mp4",
    },
    {
      id: "mirage-ct-smoke-spawnpalace",
      title: "Humo — Spawn Palace",
      side: "CT",
      category: "smoke",
      to: "Spawn Palace",
      video: "/lineups/de_mirage/ct/smoke-ct-spawnPalace.mp4",
    },
    {
      id: "mirage-ct-smoke-tapete",
      title: "Humo — Tapete",
      side: "CT",
      category: "smoke",
      to: "Tapete",
      video: "/lineups/de_mirage/ct/smoke-ct-tapete.mp4",
    },
    {
      id: "mirage-ct-smoke-tapetespawn",
      title: "Humo — Tapete / Spawn",
      side: "CT",
      category: "smoke",
      to: "Tapete / Spawn",
      video: "/lineups/de_mirage/ct/smoke-ct-tapetespawn.mp4",
    },
    // ---- T ----
    {
      id: "mirage-t-moli-arenaoscuro",
      title: "Molotov — A / Arena oscura",
      side: "T",
      category: "molotov",
      to: "A - Arena oscura",
      video: "/lineups/de_mirage/t/moli-A-arenaoscuro.mp4",
    },
    {
      id: "mirage-t-moli-mid",
      title: "Molotov — Mid",
      side: "T",
      category: "molotov",
      to: "Mid",
      video: "/lineups/de_mirage/t/moli-mid.mp4",
    },
    {
      id: "mirage-t-moli-van",
      title: "Molotov — Van",
      side: "T",
      category: "molotov",
      to: "Van",
      video: "/lineups/de_mirage/t/moli-van.mp4",
    },
    {
      id: "mirage-t-popflash-a",
      title: "Popflash — A",
      side: "T",
      category: "flash",
      to: "A",
      video: "/lineups/de_mirage/t/popflash-A.mp4",
    },
    {
      id: "mirage-t-popflash-b",
      title: "Popflash — B",
      side: "T",
      category: "flash",
      to: "B",
      video: "/lineups/de_mirage/t/popflash-b.mp4",
    },
    {
      id: "mirage-t-popflash-mid",
      title: "Popflash — Mid",
      side: "T",
      category: "flash",
      to: "Mid",
      video: "/lineups/de_mirage/t/popflash-mid.mp4",
    },
    {
      id: "mirage-t-smoke-lwall",
      title: "Humo — L Wall",
      side: "T",
      category: "smoke",
      to: "L Wall",
      video: "/lineups/de_mirage/t/smoke-Lwall.mp4",
    },
    {
      id: "mirage-t-smoke-bwindow",
      title: "Humo — B Window",
      side: "T",
      category: "smoke",
      to: "B Window",
      video: "/lineups/de_mirage/t/smoke-b-window.mp4",
    },
    {
      id: "mirage-t-smoke-cabecinha",
      title: "Humo — Cabecinha",
      side: "T",
      category: "smoke",
      to: "Cabecinha",
      video: "/lineups/de_mirage/t/smoke-cabecinha.mp4",
    },
    {
      id: "mirage-t-smoke-forest",
      title: "Humo — Forest",
      side: "T",
      category: "smoke",
      to: "Forest",
      video: "/lineups/de_mirage/t/smoke-forest.mp4",
    },
    {
      id: "mirage-t-smoke-jungle",
      title: "Humo — Jungle",
      side: "T",
      category: "smoke",
      to: "Jungle",
      video: "/lineups/de_mirage/t/smoke-jungle.mp4",
    },
    {
      id: "mirage-t-smoke-liga",
      title: "Humo — Liga",
      side: "T",
      category: "smoke",
      to: "Liga",
      video: "/lineups/de_mirage/t/smoke-liga.mp4",
    },
    {
      id: "mirage-t-smoke-shortmid",
      title: "Humo — Short / Mid",
      side: "T",
      category: "smoke",
      to: "Short / Mid",
      video: "/lineups/de_mirage/t/smoke-short-mid.mp4",
    },
    {
      id: "mirage-t-smoke-ticketsct",
      title: "Humo — Tickets CT",
      side: "T",
      category: "smoke",
      to: "Tickets CT",
      video: "/lineups/de_mirage/t/smoke-ticketsCT.mp4",
    },
    {
      id: "mirage-t-smoke-ventana",
      title: "Humo — Ventana",
      side: "T",
      category: "smoke",
      to: "Ventana",
      video: "/lineups/de_mirage/t/smoke-ventana.mp4",
    },
  ],
};

function itemsFor(mapKey: string, category: Category | "all", side: Side): LineupItem[] {
  return (LINEUPS[mapKey] ?? [])
    .filter((i) => category === "all" || i.category === category)
    .filter((i) => i.side === side);
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
  const items = itemsFor(activeMap, activeCategory, activeSide);
  const total = (LINEUPS[activeMap] ?? []).length;
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
    <div className={`lineup-page-shell lineup-side-${activeSide.toLowerCase()}`}>
      <div className="lineup-page-backdrop lineup-page-backdrop-current" style={pageBackgroundStyle} />
      <div className="lineup-page-backdrop lineup-page-backdrop-next" style={nextBackgroundStyle} />
      <div className="lineup-page-content">
        <Topbar onLogout={onLogout} />

        <motion.div className="map-pool-grid" variants={staggerList} initial="hidden" animate="show">
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
    {/* Efecto atmosférico específico del mapa */}
    {m.key === "de_ancient" ? (
      <MapArenaVideo className="map-card-fx" src="/media/ancient-arena.mp4" startAt={2} />
    ) : m.key === "de_anubis" ? (
      <MapArenaVideo className="map-card-fx" src="/media/anubis-arena.mp4" startAt={2} />
    ) : m.key === "de_dust2" ? (
      <MapArenaVideo className="map-card-fx" src="/media/dust2-arena.mp4" startAt={2} />
    ) : m.key === "de_inferno" ? (
      <MapArenaVideo className="map-card-fx" src="/media/inferno-arena.mp4" startAt={2} />
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
              <img className="lineup-side-btn-logo" src="/fondo-lineups/logo-tt.jpg" alt="Logo TT" />
            </button>
            <button
              type="button"
              className={`lineup-side-btn${activeSide === "CT" ? " active-ct" : ""}`}
              onClick={() => setActiveSide("CT")}
              aria-label="Granadas CT"
              aria-pressed={activeSide === "CT"}
            >
              <img className="lineup-side-btn-logo" src="/fondo-lineups/logo-ct.jpg" alt="Logo CT" />
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
            const count = (LINEUPS[activeMap] ?? []).filter((i) => i.category === c).length;
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

        {items.length === 0 ? (
          <div className="lineup-empty">
            <span className="lineup-empty-title">
              Todavía no hay line ups guardados para {mapName}.
            </span>
            <span className="lineup-empty-sub">
              Sumá tus grabaciones en <code>frontend/public/lineups/{activeMap}/</code> y agregalas a
              la lista de este mapa en <code>LineUps.tsx</code>.
            </span>
          </div>
        ) : (
          <motion.div
            className="lineup-grid"
            variants={staggerList}
            initial="hidden"
            animate="show"
            key={`${activeMap}:${activeCategory}:${activeSide}`}
          >
            {items.map((item) => (
              <motion.div className="lineup-card" variants={cardRise} key={item.id}>
                <video
                  className="lineup-video"
                  src={item.video}
                  controls
                  controlsList="nodownload noremoteplayback"
                  disablePictureInPicture
                  preload="metadata"
                  onContextMenu={(e) => e.preventDefault()}
                />
                <div className="lineup-card-body">
                  <div className="lineup-card-head">
                    <span className={`side-tag ${item.side === "T" ? "t" : "ct"}`}>{item.side}</span>
                    <span className={`lineup-tag ${CATEGORY_CLASS[item.category]}`}>
                      {CATEGORY_LABEL[item.category]}
                    </span>
                  </div>
                  <div className="lineup-card-title">{item.title}</div>
                  <div className="lineup-card-route">
                    {item.from && <>{item.from} </>}
                    <span className="lineup-card-arrow">→</span> {item.to}
                  </div>
                  {item.notes && <div className="lineup-card-notes">{item.notes}</div>}
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}
