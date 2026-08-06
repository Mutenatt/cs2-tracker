import { useMemo } from "react";
import type { Category, LineupPin } from "./mockLineups";

interface LineupMapStageProps {
  mapKey: string;
  pins: LineupPin[];
  hoveredLineup: LineupPin | null;
  onPinEnter: (id: string) => void;
  onPinLeave: () => void;
}

const CATEGORY_CLASS: Record<Category, string> = {
  smoke: "lineup-tag-smoke",
  flash: "lineup-tag-flash",
  molotov: "lineup-tag-molotov",
  he: "lineup-tag-he",
};

const CATEGORY_LABEL: Record<Category, string> = {
  smoke: "Humo",
  flash: "Flash",
  molotov: "Molotov",
  he: "Granada HE",
};

export function LineupMapStage({
  mapKey,
  pins,
  hoveredLineup,
  onPinEnter,
  onPinLeave,
}: LineupMapStageProps) {
  const tooltipStyle = useMemo(() => {
    if (!hoveredLineup) return {};

    const offsetPct = 8;
    const leftPct = hoveredLineup.startU * 100 - offsetPct;
    const topPct = hoveredLineup.startV * 100 - offsetPct - 20;

    return {
      left: `${Math.max(0, Math.min(leftPct, 92))}%`,
      top: `${Math.max(0, topPct)}%`,
    };
  }, [hoveredLineup]);

  return (
    <div className="lme-stage">
      <div className="lme-map-frame">
        <img
          src={`/radar/${mapKey}_radar_psd.png`}
          alt={mapKey}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />

        {hoveredLineup && (
          <svg className="lme-svg-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
            <line
              className={`lme-trajectory-line lme-trajectory-${hoveredLineup.category}`}
              x1={hoveredLineup.startU * 100}
              y1={hoveredLineup.startV * 100}
              x2={hoveredLineup.endU * 100}
              y2={hoveredLineup.endV * 100}
            />
          </svg>
        )}

        {pins.map((pin) => (
          <div
            key={pin.id}
            className={`lme-pin lme-pin-${pin.category} ${
              hoveredLineup?.id === pin.id ? "hovered" : ""
            }`}
            style={{
              left: `${pin.endU * 100}%`,
              top: `${pin.endV * 100}%`,
            }}
            onMouseEnter={() => onPinEnter(pin.id)}
            onMouseLeave={onPinLeave}
            role="button"
            tabIndex={0}
            aria-label={`${CATEGORY_LABEL[pin.category]} en ${pin.label}`}
          />
        ))}

        {hoveredLineup && (
          <div className="lme-tooltip" style={tooltipStyle}>
            <div className="lme-tooltip-video-wrap">
              <video
                className="lme-tooltip-video"
                src={hoveredLineup.videoUrl}
                autoPlay
                muted
                loop
                playsInline
              />
            </div>
            <div className="lme-tooltip-footer">
              <span className={`lineup-tag ${CATEGORY_CLASS[hoveredLineup.category]}`}>
                {CATEGORY_LABEL[hoveredLineup.category]}
              </span>
              <p className="lme-tooltip-instructions">{hoveredLineup.instructions}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
