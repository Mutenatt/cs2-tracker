import type { ReactNode } from "react";

export function SectionLabel({ children }: { children: ReactNode }) {
  return <span className="cs-section-label">{children}</span>;
}
