import { useEffect, useState } from "react";
import { getProfileTags } from "../api";
import type { ProfileTag } from "../types";

// Etiquetas visibles por tag_id (el backend manda slugs estables).
const LABELS: Record<string, string> = {
  lurkea_mucho: "Lurkea mucho",
  jugador_agresivo: "Jugador agresivo",
  maquina_de_dano: "Máquina de daño",
  alta_participacion: "Alta participación",
};

export function ProfileTagChips({ steamid }: { steamid: string }) {
  const [tags, setTags] = useState<ProfileTag[] | null>(null);

  useEffect(() => {
    setTags(null);
    getProfileTags(steamid)
      .then((r) => setTags(r.tags))
      .catch(() => setTags([]));
  }, [steamid]);

  if (!tags || tags.length === 0) return null;

  return (
    <div className="ptag-strip">
      {tags.map((t) => (
        <span
          className="ptag"
          key={t.tag_id}
          title={`Calculado sobre las últimas ${t.ventana_partidas} partidas`}
        >
          {LABELS[t.tag_id] ?? t.tag_id}
        </span>
      ))}
    </div>
  );
}
