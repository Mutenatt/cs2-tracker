import { SVGProps } from "react";
import type { Category } from "./types";

interface GrenadeIconProps extends SVGProps<SVGSVGElement> {
  category: Category;
  size?: number;
}

export function GrenadeIcon({ category, size = 16, ...props }: GrenadeIconProps) {
  const glyphs: Record<Category, React.ReactNode> = {
    smoke: (
      // Cilindro/canister redondeado
      <>
        <circle cx="12" cy="8" r="3" fill="none" strokeLinecap="round" />
        <path
          d="M 9 6 L 9 4 C 9 3 10 2 12 2 C 14 2 15 3 15 4 L 15 6"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <rect x="9" y="6" width="6" height="9" rx="1" fill="none" />
        <path d="M 10 15 L 14 15" strokeLinecap="round" />
      </>
    ),
    flash: (
      // Forma de ráfaga/estallido
      <>
        <path
          d="M 12 2 L 15 10 L 8 10 L 12 18 L 9 12 L 16 12 Z"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </>
    ),
    molotov: (
      // Botella con llama estilizada
      <>
        <path
          d="M 11 2 L 11 7 L 9 9 L 9 15 C 9 16.1 9.9 17 11 17 C 12.1 17 13 16.1 13 15 L 13 9 L 11 7"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M 10 5 L 12 2 L 14 5" fill="none" strokeLinecap="round" />
      </>
    ),
    he: (
      // Esfera fragmentada / granada
      <>
        <circle cx="12" cy="10" r="5" fill="none" strokeLinecap="round" />
        <circle cx="12" cy="10" r="3" fill="none" opacity="0.5" />
        <path d="M 12 3 L 12 1" strokeLinecap="round" />
        <path d="M 17 10 L 19 10" strokeLinecap="round" />
        <path d="M 15.5 15.5 L 16.9 16.9" strokeLinecap="round" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
      {...props}
    >
      {glyphs[category]}
    </svg>
  );
}
