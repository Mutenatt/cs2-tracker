import type { TopWeaponEntry } from "../types";
import { WeaponCategoryIcon } from "./WeaponCategoryIcon";

const NICE: Record<string, string> = {
  ak47: "AK-47",
  m4a1: "M4A4",
  m4a1_silencer: "M4A1-S",
  awp: "AWP",
  hkp2000: "USP/P2000",
  glock: "Glock",
  deagle: "Desert Eagle",
  usp_silencer: "USP-S",
  galilar: "Galil",
  famas: "FAMAS",
  mp9: "MP9",
};
const nice = (w: string) => NICE[w] ?? w;

const CATEGORY_LABEL: Record<string, string> = {
  rifle: "Rifles de asalto",
  pistol: "Armas secundarias",
  smg: "Subfusiles",
  sniper: "Rifles de precisión",
  shotgun: "Escopetas",
};

export function TopWeaponsPanel({ weapons }: { weapons: TopWeaponEntry[] }) {
  return (
    <div className="panel-card">
      <div className="panel-title">Armas principales</div>
      {weapons.length === 0 ? (
        <p className="muted">Todavía no hay kills registrados.</p>
      ) : (
        <div className="weapon-rows">
          {weapons.map((w) => (
            <div className="weapon-row" key={w.name}>
              <WeaponCategoryIcon category={w.category} />
              <div>
                <div className="wr-name">{nice(w.name)}</div>
                <div className="wr-category">{CATEGORY_LABEL[w.category] ?? w.category}</div>
              </div>
              <div className="wr-kills">
                <b>{w.kills}</b>
                <div className="wr-kills-label">kills</div>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="panel-cta">Ver todas las armas</div>
    </div>
  );
}
