import { useEffect } from "react";
import type { Category, MapPin } from "./types";

interface LineupVideoModalProps {
  pin: MapPin;
  onClose: () => void;
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

export function LineupVideoModal({ pin, onClose }: LineupVideoModalProps) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="lme-modal-overlay" onClick={onClose}>
      <div
        className="lme-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`${CATEGORY_LABEL[pin.category]} en ${pin.label}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="lme-modal-close" onClick={onClose} aria-label="Cerrar">
          ×
        </button>

        <div className="lme-modal-media">
          <video
            className="lme-modal-video"
            src={pin.videoUrl}
            controls
            autoPlay
            muted
            loop
            playsInline
            controlsList="nodownload noremoteplayback"
            disablePictureInPicture
          />
        </div>

        <div className="lme-modal-body">
          <div className="lme-modal-head">
            <span className={`lineup-tag ${CATEGORY_CLASS[pin.category]}`}>
              {CATEGORY_LABEL[pin.category]}
            </span>
            {pin.team && <span className="lme-modal-team">{pin.team}</span>}
          </div>

          <h3 className="lme-modal-title">{pin.label}</h3>

          <div className="lme-modal-section">
            <span className="lme-modal-section-title">Mirilla</span>
            <p className="lme-modal-section-text">
              {pin.crosshairNote ?? "Sin referencia de mirilla cargada todavía para este lineup."}
            </p>
          </div>

          <div className="lme-modal-section">
            <span className="lme-modal-section-title">Lanzamiento</span>
            <p className="lme-modal-section-text">
              {pin.instructions ?? "Sin nota de lanzamiento cargada todavía para este lineup."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
