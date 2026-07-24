import { useEffect, useRef, useState } from "react";

export interface MatchTypeFilterValue {
  premier: boolean;
  competitivo: boolean;
}

export function MatchTypeFilter({
  value,
  onChange,
}: {
  value: MatchTypeFilterValue;
  onChange: (v: MatchTypeFilterValue) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const toggle = (key: keyof MatchTypeFilterValue) => {
    const next = { ...value, [key]: !value[key] };
    // Al menos un tipo tiene que quedar activo.
    if (!next.premier && !next.competitivo) return;
    onChange(next);
  };

  const label =
    value.premier && value.competitivo ? "Todas" : value.premier ? "Premier" : "Competitivo";

  return (
    <div className="mtf" ref={ref}>
      <button className="mtf-trigger" onClick={() => setOpen((o) => !o)} type="button">
        {label} <span className="mtf-caret">▾</span>
      </button>
      {open && (
        <div className="mtf-menu">
          <label className="mtf-option">
            <input type="checkbox" checked={value.premier} onChange={() => toggle("premier")} />
            Premier
          </label>
          <label className="mtf-option">
            <input
              type="checkbox"
              checked={value.competitivo}
              onChange={() => toggle("competitivo")}
            />
            Competitivo
          </label>
        </div>
      )}
    </div>
  );
}
