import { Link } from "react-router-dom";
import { Loader2, Shield, Target } from "lucide-react";

// Módulo 3D desactivado a propósito: NO importar AimTrainer3D ni nada de
// src/components/game/ acá. Esa carpeta arrastra three.js/@react-three/*
// (varios MB) y los .glb de public/ -- mientras esta vista se limite a
// texto e íconos de lucide-react, ese peso ni se descarga en este bundle.
const FUTURE_FEATURES = [
  { icon: "🔫", label: "Modelos FPOV reales (AK-47 con brazos y Karambit)" },
  { icon: "🗺️", label: "Rotación de mapas más allá de Mirage" },
  { icon: "🎯", label: "Rutinas de prefire con puntaje y ranking" },
];

export function PrefireView() {
  return (
    <div className="prefire-route-shell">
      <div className="prefire-route-topbar">
        <Link to="/" className="prefire-back-btn">
          ← Dashboard
        </Link>
        <div className="prefire-map-switch" title="Más mapas próximamente">
          <span className="prefire-map-switch-label">Mapa</span>
          <span className="prefire-map-switch-value">Mirage</span>
        </div>
      </div>

      <div className="prefire-devmode">
        <div className="prefire-devmode-grid" aria-hidden />
        <div className="prefire-devmode-content">
          <div className="prefire-devmode-icon">
            <Target size={40} strokeWidth={1.5} />
          </div>

          <h1 className="prefire-devmode-title">MÓDULO 3D // EN DESARROLLO</h1>

          <p className="prefire-devmode-subtitle">
            Estamos calibrando el sistema de inventario, ver skins en tiempo real.
          </p>

          <div className="prefire-devmode-card">
            <div className="prefire-devmode-card-head">
              <Shield size={16} strokeWidth={2} />
              <span>Features futuras</span>
            </div>
            <ul className="prefire-devmode-feature-list">
              {FUTURE_FEATURES.map((feature) => (
                <li key={feature.label} className="prefire-devmode-feature">
                  <span className="prefire-devmode-feature-icon" aria-hidden>
                    {feature.icon}
                  </span>
                  <span>{feature.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="prefire-devmode-status">
            <Loader2 size={14} className="prefire-devmode-spinner" strokeWidth={2.5} />
            <span>Calibrando sistemas…</span>
          </div>

          <Link to="/" className="cs-btn cs-btn-primary prefire-devmode-cta">
            Volver al Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
