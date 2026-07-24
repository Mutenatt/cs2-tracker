import { useState } from "react";
import { motion } from "motion/react";
import { SectionLabel } from "../components/SectionLabel";
import { cardRise, staggerList } from "../components/motion/presets";

type Side = "T" | "CT";
type Category = "smoke" | "flash" | "molotov" | "boost";

interface MapEntry {
  key: string;
  name: string;
}

interface LineupItem {
  id: string;
  title: string;
  side: Side;
  category: Category;
  from: string;
  to: string;
  video: string;
  notes?: string;
}

// Mismo pool de radares que ya viven en frontend/public/maps -- se reusan
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
  boost: "Boost",
};

const CATEGORY_CLASS: Record<Category, string> = {
  smoke: "lineup-tag-smoke",
  flash: "lineup-tag-flash",
  molotov: "lineup-tag-molotov",
  boost: "lineup-tag-boost",
};

// Data de ejemplo -- cada video vive en frontend/public/lineups/{mapa}/.
// Sumar un mapa nuevo es agregar la entrada acá + tirar el .mp4 en esa
// carpeta; sin entradas, el mapa cae directo al estado vacío.
const LINEUPS: Record<string, LineupItem[]> = {
  de_mirage: [
    {
      id: "mirage-smoke-jungle-from-t",
      title: "Humo Jungle desde T spawn",
      side: "T",
      category: "smoke",
      from: "T spawn",
      to: "Jungle / conector a mid",
      video: "/lineups/de_mirage/smoke-jungle-tspawn.mp4",
      notes: "Salto + tirar apenas cruza el arco. Tapa la rotación de mid a A.",
    },
    {
      id: "mirage-flash-window-mid",
      title: "Flash ciega Window para cruzar mid",
      side: "T",
      category: "flash",
      from: "Mid",
      to: "Window (CT)",
      video: "/lineups/de_mirage/flash-window-mid.mp4",
    },
    {
      id: "mirage-molotov-default-a",
      title: "Molotov default plant A",
      side: "CT",
      category: "molotov",
      from: "A site",
      to: "Default plant",
      video: "/lineups/de_mirage/molotov-default-a.mp4",
      notes: "Post-plant: obliga al retake a entrar por Ramp.",
    },
  ],
  de_inferno: [
    {
      id: "inferno-smoke-banana",
      title: "Humo Banana desde CT spawn",
      side: "CT",
      category: "smoke",
      from: "CT spawn",
      to: "Banana",
      video: "/lineups/de_inferno/smoke-banana-ct.mp4",
    },
    {
      id: "inferno-boost-secondmid",
      title: "Boost Second Mid para picoteo",
      side: "T",
      category: "boost",
      from: "Second mid",
      to: "Banana / arch",
      video: "/lineups/de_inferno/boost-secondmid.mp4",
    },
  ],
};

function itemsFor(mapKey: string, category: Category | "all"): LineupItem[] {
  const all = LINEUPS[mapKey] ?? [];
  if (category === "all") return all;
  return all.filter((i) => i.category === category);
}

export function LineUps() {
  const [activeMap, setActiveMap] = useState(
    MAP_POOL.find((m) => m.key === "de_mirage")?.key ?? MAP_POOL[0].key,
  );
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");

  const mapName = MAP_POOL.find((m) => m.key === activeMap)?.name ?? activeMap;
  const items = itemsFor(activeMap, activeCategory);
  const total = (LINEUPS[activeMap] ?? []).length;

  return (
    <>
      <div className="section-head">
        <SectionLabel>Utilidad · Line ups</SectionLabel>
        <span className="rule" />
      </div>
      <div className="section-note" style={{ marginTop: -4 }}>
        Tu propio banco de humos, flashes y molotovs por mapa — grabalos en el juego y sumalos
        acá para tenerlos a mano antes de cada partida.
      </div>

      <motion.div className="map-pool-grid" variants={staggerList} initial="hidden" animate="show">
        {MAP_POOL.map((m) => (
          <motion.button
            key={m.key}
            type="button"
            className={`map-pool-card lineup-map-card${m.key === activeMap ? " active" : ""}`}
            variants={cardRise}
            onClick={() => setActiveMap(m.key)}
          >
            <img
              className="map-pool-icon"
              src={`/map-icons/${m.key}.png`}
              alt={m.name}
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
              }}
            />
            <span className="map-pool-name">{m.name}</span>
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
              className={`lineup-filter${activeCategory === c ? " active" : ""}`}
              onClick={() => setActiveCategory(c)}
            >
              {CATEGORY_LABEL[c]} ({count})
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
            Sumá tus grabaciones en <code>frontend/public/lineups/{activeMap}/</code> y agregalas
            a la lista de este mapa en <code>LineUps.tsx</code>.
          </span>
        </div>
      ) : (
        <motion.div
          className="lineup-grid"
          variants={staggerList}
          initial="hidden"
          animate="show"
          key={`${activeMap}:${activeCategory}`}
        >
          {items.map((item) => (
            <motion.div className="lineup-card" variants={cardRise} key={item.id}>
              <video className="lineup-video" src={item.video} controls preload="metadata" />
              <div className="lineup-card-body">
                <div className="lineup-card-head">
                  <span className={`side-tag ${item.side === "T" ? "t" : "ct"}`}>
                    {item.side}
                  </span>
                  <span className={`lineup-tag ${CATEGORY_CLASS[item.category]}`}>
                    {CATEGORY_LABEL[item.category]}
                  </span>
                </div>
                <div className="lineup-card-title">{item.title}</div>
                <div className="lineup-card-route">
                  {item.from} <span className="lineup-card-arrow">→</span> {item.to}
                </div>
                {item.notes && <div className="lineup-card-notes">{item.notes}</div>}
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </>
  );
}
