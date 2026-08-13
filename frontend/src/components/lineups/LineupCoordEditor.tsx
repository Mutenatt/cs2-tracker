import { useState } from "react";
import type { MapPin } from "./types";

interface LineupCoordEditorProps {
  pins: MapPin[];
  editing: boolean;
  onToggle: () => void;
}

export function LineupCoordEditor({ pins, editing, onToggle }: LineupCoordEditorProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = pins
      .map((pin) => `${pin.id} -> x: ${pin.x.toFixed(3)}, y: ${pin.y.toFixed(3)}`)
      .join("\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="lme-coord-editor">
      <button
        type="button"
        className={`lme-coord-toggle ${editing ? "active" : ""}`}
        onClick={onToggle}
      >
        {editing ? "Salir de modo edición" : "Ajustar posiciones"}
      </button>

      {editing && (
        <div className="lme-coord-panel">
          <div className="lme-coord-panel-head">
            <span>Arrastrá los pines sobre el mapa. Coordenadas en vivo:</span>
            <button type="button" className="lme-coord-copy" onClick={handleCopy}>
              {copied ? "Copiado ✓" : "Copiar todo"}
            </button>
          </div>
          <ul className="lme-coord-list">
            {pins.map((pin) => (
              <li key={pin.id}>
                <span className="lme-coord-label">{pin.label}</span>
                <span className="lme-coord-value">
                  x: {pin.x.toFixed(3)} y: {pin.y.toFixed(3)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
