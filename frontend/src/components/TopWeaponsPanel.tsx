import { Link } from "react-router-dom";
import { niceWeaponName, WEAPON_CATEGORY_LABEL } from "../data/weaponNames";
import type { TopWeaponEntry } from "../types";
import { WeaponSilhouette } from "./WeaponSilhouette";

export function TopWeaponsPanel({
  weapons,
  steamid,
}: {
  weapons: TopWeaponEntry[];
  steamid: string;
}) {
  return (
    <div className="panel-card">
      <div className="panel-title">Armas principales</div>
      {weapons.length === 0 ? (
        <p className="muted">Todavía no hay kills registrados.</p>
      ) : (
        <div className="weapon-rows">
          {weapons.map((w) => (
            <div className="weapon-row" key={w.name}>
              <WeaponSilhouette weapon={w.name} category={w.category} />
              <div>
                <div className="wr-name">{niceWeaponName(w.name)}</div>
                <div className="wr-category">{WEAPON_CATEGORY_LABEL[w.category] ?? w.category}</div>
              </div>
              <div className="wr-kills">
                <b>{w.kills}</b>
                <div className="wr-kills-label">kills</div>
              </div>
            </div>
          ))}
        </div>
      )}
      <Link to={`/profile/${steamid}/weapons`} className="panel-cta">
        Ver todas las armas
      </Link>
    </div>
  );
}
