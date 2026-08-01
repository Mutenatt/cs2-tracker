import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getWeaponsDetail } from "../api";
import { LoadoutList } from "../components/weapons/LoadoutList";
import { SectionLabel } from "../components/SectionLabel";
import { SmoothScroll } from "../components/motion/SmoothScroll";
import { WeaponHeroGrid } from "../components/weapons/WeaponHeroGrid";
import { WeaponTable } from "../components/weapons/WeaponTable";
import type { WeaponsPageResponse } from "../types";

export function WeaponsView() {
  const { steamid } = useParams<{ steamid: string }>();
  const [data, setData] = useState<WeaponsPageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <SmoothScroll>
      <div className="section-head">
        <SectionLabel>Perfil · Armas</SectionLabel>
        <span className="rule" />
      </div>

      <div className="section-head" style={{ marginTop: 0 }}>
        <SectionLabel>Loadouts</SectionLabel>
        <span className="rule" />
      </div>
      <LoadoutList loadouts={data.loadouts} />

      <div className="section-head">
        <SectionLabel>Weapons</SectionLabel>
        <span className="rule" />
      </div>

      <WeaponHeroGrid weapons={data.weapons} />
      <WeaponTable weapons={data.weapons} />
    </SmoothScroll>
  );
}
