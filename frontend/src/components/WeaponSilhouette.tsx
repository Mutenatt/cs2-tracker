import { useState } from "react";
import type { WeaponCategory } from "../types";
import { WeaponCategoryIcon } from "./WeaponCategoryIcon";

// Ícono real por arma: SVG oficial de CS2 en public/weapons/{weapon}.svg
// (nombrado con la misma clave que manda demoparser2 -- sin remapeo). Si
// el archivo no existe (ej. una variante de cuchillo sin asset propio)
// cae al line-art genérico de categoría, mismo patrón de fallback que
// TeamLogo en HomeView.tsx.
export function WeaponSilhouette({
  weapon,
  category,
  width = 40,
  height = 16,
}: {
  weapon: string;
  category: WeaponCategory;
  width?: number;
  height?: number;
}) {
  const [broken, setBroken] = useState(false);
  if (broken) return <WeaponCategoryIcon category={category} width={width} height={height} />;
  return (
    <img
      src={`/weapons/${weapon}.svg`}
      alt={weapon}
      style={{ width, height, objectFit: "contain" }}
      onError={() => setBroken(true)}
    />
  );
}
