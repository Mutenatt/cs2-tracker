import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "motion/react";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* reducedMotion="user": Motion desactiva sus animaciones si el sistema
          pide movimiento reducido, igual que el reset de styles.css */}
      <MotionConfig reducedMotion="user">
        {/* Fondo cinemático global (glow + dot grid): por fuera de <App/> para
            que no se remonte ni "corte" entre vistas al navegar. */}
        <div className="app-atmosphere">
          <div className="app-atmosphere-glow app-atmosphere-glow-cyan" aria-hidden="true" />
          <div className="app-atmosphere-glow app-atmosphere-glow-blue" aria-hidden="true" />
          <div className="app-atmosphere-grid" aria-hidden="true" />
          <div className="app-atmosphere-content">
            <App />
          </div>
        </div>
      </MotionConfig>
    </BrowserRouter>
  </React.StrictMode>
);
