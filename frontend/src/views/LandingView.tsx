import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { livePulse } from "../components/motion/presets";

export function LandingView() {
  return (
    <div className="landing-view">
      <div className="landing-topbar">
        <Logo size={20} />
        <div className="live landing-live">
          <motion.span className="dot" variants={livePulse} animate="pulse" />
          <span>Datos en vivo</span>
        </div>
      </div>

      <div className="landing-hero">
        <h1 className="landing-hero-title">
          Estadísticas y trackeo de rendimiento, <span>con tus clutches listos para subir</span>
        </h1>
        <p className="landing-hero-sub">
          Soñar con jugar profesional es fácil. Ser lo suficientemente crítico con vos mismo para
          lograrlo, no tanto.
        </p>
        <span className="landing-hero-kicker">Empezá el camino a tu sueño</span>
        <div className="landing-hero-ctas">
          <Link className="cs-btn cs-btn-primary landing-hero-cta" to="/register">
            Crear cuenta
          </Link>
          <Link className="cs-btn cs-btn-ghost landing-hero-cta" to="/login">
            Iniciar sesión
          </Link>
        </div>
      </div>

      <div id="demo" className="landing-section">
        <div className="landing-label landing-label-signal landing-center">
          Momentos que valen un clip
        </div>
        <h2 className="landing-h2 landing-center">cStats te marca el minuto exacto</h2>
        <div className="landing-demo-frame">
          {/* Placeholder — reemplazar por captura real del producto (timeline de clutches / duelos) */}
          <div className="landing-demo-placeholder">
            Captura de la línea de clutches / duelos destacados
          </div>
        </div>
      </div>

      <div className="landing-section">
        <div className="landing-label landing-label-signal">Contenido que se prepara solo</div>
        <h2 className="landing-h2 landing-h2-narrow">De demo cruda a segmento de stream</h2>
        <div className="landing-features-grid">
          <Card className="landing-feature-card">
            <div className="landing-feature-icon landing-feature-icon-alert">
              <span className="landing-feature-icon-dot" />
            </div>
            <div className="landing-feature-title">Timeline de clutches</div>
            <p className="landing-feature-desc">
              Cada 1vX ganado o perdido, marcado con la ronda exacta. Encontrá el highlight sin
              scrubear la demo entera.
            </p>
          </Card>
          <Card className="landing-feature-card">
            <span className="landing-feature-pro-badge">Pro · Próximamente</span>
            <div className="landing-feature-icon landing-feature-icon-gold">
              <span className="landing-feature-icon-play" />
            </div>
            <div className="landing-feature-title">Clip 2D de tu radar</div>
            <p className="landing-feature-desc">
              Cada ACE, multi-kill o clutch se detecta solo y se renderiza en video vertical con el
              radar, las posiciones y el killfeed — sin tocar un editor.
            </p>
          </Card>
          <Card className="landing-feature-card">
            <span className="landing-feature-pro-badge">Pro · Próximamente</span>
            <div className="landing-feature-icon landing-feature-icon-go">
              <span className="landing-feature-icon-phone" />
            </div>
            <div className="landing-feature-title">Recortes listos para tu feed</div>
            <p className="landing-feature-desc">
              Bajá el clip en vertical (TikTok/Reels/Shorts) apenas termina de renderizar. Tu
              nombre, el mapa y la ronda ya vienen encima — subilo tal cual.
            </p>
          </Card>
        </div>
      </div>

      <div className="landing-stats-strip">
        <div className="landing-stats-grid">
          <div className="landing-stat">
            <div className="landing-stat-value landing-stat-value-recon">600+</div>
            <div className="landing-stat-label">creadores usando cStats</div>
          </div>
          <div className="landing-stat">
            <div className="landing-stat-value">3.2K</div>
            <div className="landing-stat-label">clips detectados / semana</div>
          </div>
          <div className="landing-stat">
            <div className="landing-stat-value landing-stat-value-signal">&lt;30s</div>
            <div className="landing-stat-label">tiempo de análisis</div>
          </div>
          <div className="landing-stat">
            <div className="landing-stat-value landing-stat-value-go">100%</div>
            <div className="landing-stat-label">local, tu cuenta a salvo</div>
          </div>
        </div>
      </div>

      <div className="landing-final-cta">
        <h2 className="landing-h2">
          Tu próximo clip ya pasó.
          <br />
          Solo falta encontrarlo.
        </h2>
        <p className="landing-final-cta-sub">
          Perfecciona tu gameplay con cStats y comparti al mundo tus momentos más destacados.{" "}
        </p>
        <Link className="cs-btn cs-btn-primary landing-hero-cta" to="/register">
          Crear cuenta
        </Link>
      </div>

      <div className="landing-footer">
        <Logo size={14} />
        <div className="landing-footer-links">
          <a href="#">Términos</a>
          <a href="#">Privacidad</a>
          <a href="#">Contacto</a>
        </div>
      </div>
    </div>
  );
}
