import { useState } from "react";
import { niceWeaponName, WEAPON_CATEGORY_LABEL } from "../../data/weaponNames";
import { WeaponSilhouette } from "../WeaponSilhouette";
import type { WeaponCategory, WeaponDetailEntry } from "../../types";

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

const HS_HOT_THRESHOLD = 50;

export function WeaponTable({ weapons }: { weapons: WeaponDetailEntry[] }) {
  const [activeCategory, setActiveCategory] = useState<WeaponCategory | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("kills");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const filtered = weapons.filter((w) => activeCategory === "all" || w.category === activeCategory);
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
      <div className="weapon-cat-bar">
        <button
          type="button"
          className={`weapon-cat-pill${activeCategory === "all" ? " active" : ""}`}
          onClick={() => setActiveCategory("all")}
        >
          Todas las armas
        </button>
        {CATEGORY_ORDER.map((c) => (
          <button
            key={c}
            type="button"
            className={`weapon-cat-pill${activeCategory === c ? " active" : ""}`}
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
              <span className="mono wt-value">{w.kills}</span>
              <span className="mono wt-value">{w.deaths}</span>
              <div className="wt-hs-cell">
                <span className="mono wt-value">{w.hs_pct.toFixed(1)}%</span>
                <span className="wt-hs-bar" aria-hidden="true">
                  <span
                    className={`wt-hs-bar-fill${w.hs_pct >= HS_HOT_THRESHOLD ? " hot" : ""}`}
                    style={{ width: `${Math.min(100, w.hs_pct)}%` }}
                  />
                </span>
              </div>
              <span className="mono wt-value">{w.adr.toFixed(1)}</span>
              <span className="mono wt-value">{w.kills_per_round.toFixed(2)}</span>
              <span className="mono wt-value">{w.longest_kill_m.toFixed(1)} m</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
