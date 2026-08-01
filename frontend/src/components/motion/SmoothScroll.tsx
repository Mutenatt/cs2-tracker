import type { ReactNode } from "react";
import { ReactLenis } from "lenis/react";
import "lenis/dist/lenis.css";

const LENIS_OPTIONS = {
  duration: 1.1,
  smoothWheel: true,
  wheelMultiplier: 1,
  touchMultiplier: 1.2,
};

// Scroll con inercia (rueda del ratón) para las vistas de contenido largo
// (LandingView, HomeView, ProfileView, MatchDetailView, WeaponsView,
// SettingsView, LineUps) -- se monta/desmonta junto con la vista que lo
// envuelve, así que no toca el scroll nativo de PrefireView (landing "en
// desarrollo" liviana) ni de los formularios cortos del flujo pre-login
// (Login, Register, ForgotPassword, ResetPassword).
export function SmoothScroll({ children }: { children: ReactNode }) {
  return (
    <ReactLenis root options={LENIS_OPTIONS}>
      {children}
    </ReactLenis>
  );
}
