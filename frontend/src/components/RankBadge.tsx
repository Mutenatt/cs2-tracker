// Badge de CS Rating estilo CS2 Premier: paralelogramo oscuro con el número
// coloreado por tier (paleta oficial de CS2, no tokens del tema — es marca).
// Se renderiza solo con rank > 0 y rank_type Premier (11) o desconocido.

const TIERS: [number, string][] = [
  [30000, "t7"], // dorado
  [25000, "t6"], // rojo
  [20000, "t5"], // fucsia
  [15000, "t4"], // violeta
  [10000, "t3"], // azul
  [5000, "t2"], // celeste
  [0, "t1"], // gris
];

// Exportada: el header del perfil reutiliza la misma paleta de tiers.
export function tierClass(rank: number): string {
  return TIERS.find(([min]) => rank >= min)![1];
}

export function RankBadge({ rank, rankType }: { rank: number | null; rankType: number | null }) {
  if (rank === null || rank <= 0) return null;
  if (rankType !== null && rankType !== 11) return null; // solo Premier

  const thousands = Math.floor(rank / 1000);
  const rest = String(rank % 1000).padStart(3, "0");

  return (
    <span
      className={`rank-badge ${tierClass(rank)}`}
      title={`CS Rating ${rank.toLocaleString("es")}`}
    >
      <span className="rb-inner mono">
        {thousands > 0 ? (
          <>
            <b>
              {thousands}
              <span className="rb-sep">,</span>
            </b>
            <small>{rest}</small>
          </>
        ) : (
          <b>{rank}</b>
        )}
      </span>
    </span>
  );
}
