import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "ghost";
type CommonProps = { variant?: Variant; className?: string; children: ReactNode };
type AsButton = CommonProps & { as?: "button" } & ButtonHTMLAttributes<HTMLButtonElement>;
type AsAnchor = CommonProps & { as: "a" } & AnchorHTMLAttributes<HTMLAnchorElement>;

export function Button({ variant = "primary", className = "", as, ...rest }: AsButton | AsAnchor) {
  const cls = `cs-btn cs-btn-${variant} ${className}`.trim();
  if (as === "a")
    return <a className={cls} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)} />;
  return <button className={cls} {...(rest as ButtonHTMLAttributes<HTMLButtonElement>)} />;
}
