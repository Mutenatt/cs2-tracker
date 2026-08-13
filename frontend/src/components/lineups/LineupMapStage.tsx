import { useRef, useState } from "react";
import type { Category, MapPin } from "./types";

interface LineupMapStageProps {
  mapKey: string;
  pins: MapPin[];
  hoveredId: string | null;
  onPinHoverStart: (id: string) => void;
  onPinHoverEnd: () => void;
  onPinSelect: (pin: MapPin) => void;
  editable?: boolean;
  onPinDrag?: (id: string, x: number, y: number) => void;
}

const CATEGORY_LABEL: Record<Category, string> = {
  smoke: "Humo",
  flash: "Flash",
  molotov: "Molotov",
  he: "Granada HE",
};

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}

export function LineupMapStage({
  mapKey,
  pins,
  hoveredId,
  onPinHoverStart,
  onPinHoverEnd,
  onPinSelect,
  editable = false,
  onPinDrag,
}: LineupMapStageProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const hoveredPin = pins.find((p) => p.id === hoveredId) ?? null;
  const hoveredTrajectory =
    hoveredPin && hoveredPin.startX !== undefined && hoveredPin.startY !== undefined
      ? hoveredPin
      : null;

  const dragPinTo = (clientX: number, clientY: number) => {
    const frame = frameRef.current;
    if (!frame || !draggingId || !onPinDrag) return;
    const rect = frame.getBoundingClientRect();
    const x = clamp01((clientX - rect.left) / rect.width);
    const y = clamp01((clientY - rect.top) / rect.height);
    onPinDrag(draggingId, x, y);
  };

  return (
    <div className="lme-stage">
      <div
        ref={frameRef}
        className="lme-map-frame"
        onPointerMove={(e) => {
          if (draggingId) dragPinTo(e.clientX, e.clientY);
        }}
        onPointerUp={() => setDraggingId(null)}
        onPointerLeave={() => setDraggingId(null)}
      >
        <img
          src={`/radar/${mapKey}_radar_psd.png`}
          alt={mapKey}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />

        {hoveredTrajectory && (
          <svg className="lme-svg-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
            <line
              className={`lme-trajectory-line lme-trajectory-${hoveredTrajectory.category}`}
              x1={hoveredTrajectory.startX! * 100}
              y1={hoveredTrajectory.startY! * 100}
              x2={hoveredTrajectory.x * 100}
              y2={hoveredTrajectory.y * 100}
            />
          </svg>
        )}

        {pins.map((pin) => (
          <button
            key={pin.id}
            type="button"
            className={`lme-pin lme-pin-${pin.category} ${hoveredId === pin.id ? "hovered" : ""} ${editable ? "editable" : ""} ${draggingId === pin.id ? "dragging" : ""}`}
            style={{
              left: `${pin.x * 100}%`,
              top: `${pin.y * 100}%`,
            }}
            onMouseEnter={() => onPinHoverStart(pin.id)}
            onMouseLeave={onPinHoverEnd}
            onFocus={() => onPinHoverStart(pin.id)}
            onBlur={onPinHoverEnd}
            onClick={() => {
              if (!editable) onPinSelect(pin);
            }}
            onPointerDown={(e) => {
              if (!editable) return;
              e.preventDefault();
              e.stopPropagation();
              setDraggingId(pin.id);
            }}
            aria-label={`${CATEGORY_LABEL[pin.category]} en ${pin.label}`}
            title={
              editable ? `${pin.label} — x:${pin.x.toFixed(3)} y:${pin.y.toFixed(3)}` : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}
