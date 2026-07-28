interface MapStatsPopoverProps {
  map: string;
  winRate: number | null;
}

// Icono flotante (esquina del carrusel de "mejor mapa" en el perfil, ver
// ProfileView.tsx) que reemplaza el texto estático "Mejor mapa · Anubis ·
// XX% WR" -- la info ahora vive en una burbuja que aparece al hover/focus.
export function MapStatsPopover({ map, winRate }: MapStatsPopoverProps) {
  const mapName = map.replace(/^de_/, "");

  return (
    <span className="map-stats-popover" tabIndex={0}>
      <img
        className="map-stats-popover-icon"
        src="/assets-perfil/map-stats-help.png"
        alt="Info de tu mejor mapa"
      />
      <span className="map-stats-popover-bubble" role="tooltip">
        Tu mejor mapa es <b>{mapName}</b>
        {winRate !== null && (
          <>
            {" "}
            con un <b>{winRate.toFixed(0)}%</b> de winrate
          </>
        )}
      </span>
    </span>
  );
}
