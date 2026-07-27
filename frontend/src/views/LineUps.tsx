import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { CenoteWaterBackground } from "../components/CenoteWaterBackground";
import { DesertDuneBackground } from "../components/DesertDuneBackground";
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
  molotov: 1650,
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

function UtilityButtonEffect({ category }: { category: Category }) {
  const particles = category === "smoke" ? 5 : category === "molotov" ? 6 : 8;
  return (
    <span className={`lineup-filter-effect lineup-filter-effect-${category}`} aria-hidden="true">
      {category === "molotov" ? (
        <img className="lineup-molotov-fire" src="/effects/molotov-fire.svg" alt="" />
      ) : (
        Array.from({ length: particles }, (_, index) => <i key={index} />)
      )}
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
        <div className="section-head">
          <SectionLabel>Utilidad · Line ups</SectionLabel>
          <span className="rule" />
        </div>
        <div className="section-note" style={{ marginTop: -4 }}>
          Tu propio banco de humos, flashes y molotovs por mapa — grabalos en el juego y sumalos acá
          para tenerlos a mano antes de cada partida.
        </div>

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
      <CenoteWaterBackground className="map-card-fx" />
    ) : m.key === "de_anubis" ? (
      <DesertDuneBackground className="map-card-fx" />
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

        <div className="lineup-filters">
          <button
            type="button"
            className={`lineup-filter lineup-filter-side${activeSide === "T" ? " active-t" : ""}`}
            onClick={() => setActiveSide("T")}
          >
            Granadas TT
          </button>
          <button
            type="button"
            className={`lineup-filter lineup-filter-side${activeSide === "CT" ? " active-ct" : ""}`}
            onClick={() => setActiveSide("CT")}
          >
            Granadas CT
          </button>
        </div>

        <div className="lineup-filters">
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
