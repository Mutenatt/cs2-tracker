interface Props {
  headColor: string;
  bodyColor: string;
  legsColor: string;
}

// Silueta propia (no es un asset del juego), zonas como <polygon> separados
// para poder colorear cada uno por código. Puntos ver feacture_nuevo.md.
export function AccuracySilhouette({ headColor, bodyColor, legsColor }: Props) {
  return (
    <svg viewBox="0 0 60 130" style={{ width: 44, height: 96, flex: "0 0 auto" }}>
      <polygon points="26,13 34,13 37,20 35,27 25,27 23,20" fill={headColor} />
      <polygon points="25,31 35,31 39,43 37,71 30,84 23,71 21,43" fill={bodyColor} />
      <polygon points="23.5,31 14,39 12,71 21,72 19,44" fill={bodyColor} />
      <polygon points="36.5,31 46,39 48,71 39,72 41,44" fill={bodyColor} />
      <polygon points="22,73 29,86 26,125 19,125" fill={legsColor} />
      <polygon points="38,73 31,86 34,125 41,125" fill={legsColor} />
    </svg>
  );
}
