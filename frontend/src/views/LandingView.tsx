import { motion } from "motion/react";
import { loginUrl } from "../api";
import { Button } from "../components/Button";
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
        <Button as="a" href={loginUrl()} className="landing-topbar-cta">
          Iniciar con Steam
        </Button>
      </div>

      <div className="landing-hero">
        <h1 className="landing-hero-title">
          Estadísticas y trackeo de rendimiento, <span>con tus clutches listos para subir</span>
        </h1>
        <p className="landing-hero-sub">
          cStats analiza cada demo de CS2, extrae tus métricas de rendimiento y detecta
          automáticamente tus clutches y duelos clave — recortados y listos para publicar.
        </p>
        <div className="landing-hero-ctas">
          <Button as="a" href={loginUrl()} className="landing-hero-cta">
            Iniciar sesión con Steam
          </Button>
        </div>
        <a href="#demo" className="landing-anchor-link">
          Ver cómo funciona ↓
        </a>
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
            <div className="landing-feature-icon landing-feature-icon-signal">
              <span className="landing-feature-icon-vs">VS</span>
            </div>
            <div className="landing-feature-title">Head-to-head narrable</div>
            <p className="landing-feature-desc">
              La matriz de duelos contra cada rival, con arma y distancia. Material listo para
              contarle la historia de la ronda a tu chat.
            </p>
          </Card>
          <Card className="landing-feature-card">
            <div className="landing-feature-icon landing-feature-icon-recon">
              <span className="landing-feature-icon-bars">
                <span />
                <span />
                <span />
              </span>
            </div>
            <div className="landing-feature-title">Rank history en vivo</div>
            <p className="landing-feature-desc">
              Mostrale a tu comunidad la curva completa de tu Premier Rating, partida a partida — tu
              propia narrativa de progreso.
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
        <p className="landing-final-cta-sub">Sin tarjeta. Sin publicidad. Tus datos son tuyos.</p>
        <Button as="a" href={loginUrl()} className="landing-hero-cta">
          Iniciar sesión con Steam
        </Button>
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
