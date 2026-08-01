import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { getMe, logout } from "./api";
import { Topbar } from "./components/Topbar";
import { LogoIntroTransition } from "./components/motion/LogoIntroTransition";
import { ROUTE_FADE } from "./components/motion/presets";
import { UserContext } from "./context/UserContext";
import { EmailVerificationPendingView } from "./views/EmailVerificationPendingView";
import { ForgotPasswordView } from "./views/ForgotPasswordView";
import { HomeView } from "./views/HomeView";
import { LandingView } from "./views/LandingView";
import { LineUps } from "./views/LineUps";
import { LoginView } from "./views/LoginView";
import { MatchDetailView } from "./views/MatchDetailView";
import { OnboardingView } from "./views/OnboardingView";
import { ProfileView } from "./views/ProfileView";
import { RegisterView } from "./views/RegisterView";
import { ResetPasswordView } from "./views/ResetPasswordView";
import { SettingsView } from "./views/SettingsView";
import { WeaponsView } from "./views/WeaponsView";
import type { MeOut, User } from "./types";

// Code-split igual que el resto de las rutas secundarias -- ahora mismo
// PrefireView es una landing "en desarrollo" liviana (sin three.js/rapier,
// ver PrefireView.tsx), pero mantenerla separada evita tener que tocar este
// archivo cuando el módulo 3D vuelva a activarse.
const PrefireView = lazy(() => import("./views/PrefireView").then((m) => ({ default: m.PrefireView })));

export function App() {
  const [me, setMe] = useState<MeOut | null | undefined>(undefined);
  const [authError, setAuthError] = useState(false);
  const location = useLocation();

  // Cortina de la medalla 3D entre las landings de pre-login (Landing/
  // Register/Login/etc.) -- solo se dispara en navegaciones posteriores al
  // mount inicial, nunca en la primera carga de la landing.
  const [preLoginTransitioning, setPreLoginTransitioning] = useState(false);
  const prevPreLoginPath = useRef(location.pathname);

  useEffect(() => {
    if (me !== null) return;
    if (prevPreLoginPath.current === location.pathname) return;
    prevPreLoginPath.current = location.pathname;
    setPreLoginTransitioning(true);
  }, [location.pathname, me]);

  const refreshMe = async () => {
    try {
      setMe(await getMe());
    } catch {
      setAuthError(true);
    }
  };

  useEffect(() => {
    refreshMe();
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    setMe(null);
  };

  if (authError) {
    return (
      <div className="wrap center">
        <p>No se pudo verificar tu sesión.</p>
        <button className="pill" onClick={() => window.location.reload()}>
          Reintentar
        </button>
      </div>
    );
  }
  if (me === undefined) return <div className="wrap center">Cargando…</div>;

  if (me === null) {
    return (
      <>
        <Routes location={location}>
          <Route path="/" element={<LandingView />} />
          <Route path="/register" element={<RegisterView onRegistered={refreshMe} />} />
          <Route path="/login" element={<LoginView onLoggedIn={refreshMe} />} />
          <Route path="/forgot-password" element={<ForgotPasswordView />} />
          <Route path="/reset-password" element={<ResetPasswordView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        {preLoginTransitioning && (
          <LogoIntroTransition onFinished={() => setPreLoginTransitioning(false)} />
        )}
      </>
    );
  }

  if (me.pending) {
    if (!me.email_verified_at) {
      return (
        <EmailVerificationPendingView
          email={me.email}
          onVerified={refreshMe}
          onLogout={handleLogout}
        />
      );
    }
    return <OnboardingView mode="pending" onComplete={refreshMe} />;
  }

  // me.pending === false: cuenta real, con steamid vinculado.
  const user: User = {
    steamid: me.steamid as string,
    display_name: me.display_name,
    avatar_url: me.avatar_url,
    steam_background_url: me.steam_background_url,
    email: me.email,
    email_verified_at: me.email_verified_at,
    onboarding_completed_at: me.onboarding_completed_at,
  };

  if (user.onboarding_completed_at === null) {
    return (
      <UserContext.Provider value={user}>
        <OnboardingView mode="user" onComplete={refreshMe} />
      </UserContext.Provider>
    );
  }

  const isLineupsRoute = location.pathname === "/lineups";
  const isPrefireRoute = location.pathname === "/prefire";
  const isFullscreenRoute = isLineupsRoute || isPrefireRoute;

  return (
    <UserContext.Provider value={user}>
      <div className={isFullscreenRoute ? "lineup-route-shell" : "wrap"}>
        {!isFullscreenRoute && <Topbar onLogout={handleLogout} />}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: ROUTE_FADE, ease: "linear" }}
          >
            <Routes location={location}>
              <Route path="/" element={<HomeView />} />
              <Route path="/lineups" element={<LineUps onLogout={handleLogout} />} />
              <Route
                path="/prefire"
                element={
                  <Suspense fallback={<div className="wrap center">Cargando…</div>}>
                    <PrefireView />
                  </Suspense>
                }
              />
              <Route path="/profile/:steamid" element={<ProfileView />} />
              <Route path="/profile/:steamid/weapons" element={<WeaponsView />} />
              <Route path="/match/:matchId" element={<MatchDetailView />} />
              <Route path="/settings" element={<SettingsView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </div>
    </UserContext.Provider>
  );
}
