import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "motion/react";
import { getWeaponsDetail } from "../api";
import { SectionLabel } from "../components/SectionLabel";
import { WeaponSilhouette } from "../components/WeaponSilhouette";
import { niceWeaponName, WEAPON_CATEGORY_LABEL } from "../data/weaponNames";
import { cardRise, staggerList } from "../components/motion/presets";
import type { LoadoutTier, LoadoutTierStats, WeaponCategory, WeaponsPageResponse } from "../types";

const LOADOUT_ORDER: LoadoutTier[] = ["full_buy", "semi_buy", "pistol", "eco"];

const LOADOUT_META: Record<LoadoutTier, { label: string; sub: string }> = {
  full_buy: { label: "Full", sub: ">= $3900" },
  semi_buy: { label: "Semi", sub: "$1000-3900" },
  pistol: { label: "Pistol", sub: "1ra ronda de cada mitad" },
  eco: { label: "Eco", sub: "$0-1000" },
};

const CATEGORY_ORDER: WeaponCategory[] = [
  "pistol",
  "shotgun",
  "smg",
  "rifle",
  "heavy",
  "sniper",
  "melee",
];

type SortKey = "kills" | "deaths" | "hs_pct" | "adr" | "kills_per_round" | "longest_kill_m";

const SORT_LABEL: Record<SortKey, string> = {
  kills: "Kills",
  deaths: "Deaths",
  hs_pct: "HS%",
  adr: "ADR",
  kills_per_round: "Kills/Ronda",
  longest_kill_m: "Distancia máx.",
};

function kd(l: LoadoutTierStats): string {
  return l.kd.toFixed(2);
}

export function WeaponsView() {
  const { steamid } = useParams<{ steamid: string }>();
  const [data, setData] = useState<WeaponsPageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<WeaponCategory | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("kills");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    if (!steamid) return;
    setData(null);
    setError(null);
    (async () => {
      try {
        setData(await getWeaponsDetail(steamid));
      } catch {
        setError(
          "No se pudo cargar el detalle de armas (¿compartís alguna partida con este jugador?)."
        );
      }
    })();
  }, [steamid]);

  if (error) return <p className="section-note">{error}</p>;
  if (!data) return <p className="muted">Cargando…</p>;

  const top3 = [...data.weapons].sort((a, b) => b.kills - a.kills).slice(0, 3);
  const filtered = data.weapons.filter(
    (w) => activeCategory === "all" || w.category === activeCategory
  );
  const sorted = [...filtered].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey];
    return sortDir === "desc" ? -diff : diff;
  });

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  return (
    <>
      <div className="section-head">
        <SectionLabel>Perfil · Armas</SectionLabel>
        <span className="rule" />
      </div>

      <div className="section-head" style={{ marginTop: 0 }}>
        <SectionLabel>Loadouts</SectionLabel>
        <span className="rule" />
      </div>
      <div className="loadout-table">
        <div className="loadout-row loadout-head">
          <span>Loadout</span>
          <span>K/D</span>
          <span>ADR</span>
          <span>ACS</span>
          <span>DDΔ</span>
          <span>KAST</span>
          <span>ESR</span>
          <span>Kills</span>
          <span>Deaths</span>
        </div>
        {LOADOUT_ORDER.map((tier) => {
          const t = data.loadouts.find((l) => l.tier === tier);
          if (!t) return null;
          const meta = LOADOUT_META[tier];
          return (
            <div className="loadout-row" key={tier}>
              <div className="loadout-name">
                <span className="loadout-name-label">{meta.label}</span>
                <span className="loadout-name-sub">{meta.sub}</span>
              </div>
              <b>{kd(t)}</b>
              <span>{t.adr.toFixed(1)}</span>
              <span>{t.acs.toFixed(1)}</span>
              <span
                className={t.dd > 0 ? "loadout-dd-pos" : t.dd < 0 ? "loadout-dd-neg" : undefined}
              >
                {t.dd > 0 ? "+" : ""}
                {t.dd.toFixed(1)}
              </span>
              <span>{t.kast_pct.toFixed(1)}%</span>
              <span>{t.esr_pct.toFixed(1)}%</span>
              <span>{t.kills}</span>
              <span>{t.deaths}</span>
            </div>
          );
        })}
      </div>

      <div className="section-head">
        <SectionLabel>Weapons</SectionLabel>
        <span className="rule" />
      </div>

      {top3.length > 0 && (
        <motion.div
          className="weapons-hero-grid"
          variants={staggerList}
          initial="hidden"
          animate="show"
        >
          {top3.map((w, i) => (
            <motion.div className="weapons-hero-card" variants={cardRise} key={w.name}>
              <span className={`weapon-rank-badge rank-${i + 1}`}>#{i + 1}</span>
              <WeaponSilhouette weapon={w.name} category={w.category} width={96} height={38} />
              <div className="weapons-hero-name">{niceWeaponName(w.name)}</div>
              <div className="weapons-hero-stats">
                <div>
                  <b>{w.kills}</b>
                  <span>Kills</span>
                </div>
                <div>
                  <b>{w.hs_pct.toFixed(1)}%</b>
                  <span>HS%</span>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      <div className="lineup-filters">
        <button
          type="button"
          className={`lineup-filter${activeCategory === "all" ? " active" : ""}`}
          onClick={() => setActiveCategory("all")}
        >
          Todas las armas
        </button>
        {CATEGORY_ORDER.map((c) => (
          <button
            key={c}
            type="button"
            className={`lineup-filter${activeCategory === c ? " active" : ""}`}
            onClick={() => setActiveCategory(c)}
          >
            {WEAPON_CATEGORY_LABEL[c]}
          </button>
        ))}
      </div>

      {sorted.length === 0 ? (
        <p className="muted">Sin armas en esta categoría todavía.</p>
      ) : (
        <div className="weapons-table">
          <div className="weapons-table-row weapons-table-head">
            <span>Arma</span>
            {(Object.keys(SORT_LABEL) as SortKey[]).map((key) => (
              <button
                key={key}
                type="button"
                className={`weapons-table-sort${sortKey === key ? " active" : ""}`}
                onClick={() => toggleSort(key)}
              >
                {SORT_LABEL[key]}
                {sortKey === key && (
                  <span className="weapons-table-sort-arrow">
                    {sortDir === "desc" ? " ▼" : " ▲"}
                  </span>
                )}
              </button>
            ))}
          </div>
          {sorted.map((w) => (
            <div className="weapons-table-row" key={w.name}>
              <div className="weapons-table-weapon">
                <WeaponSilhouette weapon={w.name} category={w.category} />
                <div>
                  <div className="wr-name">{niceWeaponName(w.name)}</div>
                  <div className="wr-category">
                    {WEAPON_CATEGORY_LABEL[w.category] ?? w.category}
                  </div>
                </div>
              </div>
              <span>{w.kills}</span>
              <span>{w.deaths}</span>
              <span>{w.hs_pct.toFixed(1)}%</span>
              <span>{w.adr.toFixed(1)}</span>
              <span>{w.kills_per_round.toFixed(2)}</span>
              <span>{w.longest_kill_m.toFixed(1)} m</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
