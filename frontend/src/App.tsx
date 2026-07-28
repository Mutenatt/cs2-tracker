import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { getMe, logout } from "./api";
import { Topbar } from "./components/Topbar";
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

export function App() {
  const [me, setMe] = useState<MeOut | null | undefined>(undefined);
  const [authError, setAuthError] = useState(false);
  const location = useLocation();

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
      <Routes location={location}>
        <Route path="/" element={<LandingView />} />
        <Route path="/register" element={<RegisterView onRegistered={refreshMe} />} />
        <Route path="/login" element={<LoginView onLoggedIn={refreshMe} />} />
        <Route path="/forgot-password" element={<ForgotPasswordView />} />
        <Route path="/reset-password" element={<ResetPasswordView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
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

  return (
    <UserContext.Provider value={user}>
      <div className="wrap">
        <Topbar onLogout={handleLogout} />
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
              <Route path="/lineups" element={<LineUps />} />
              <Route path="/profile/:steamid" element={<ProfileView />} />
              <Route path="/profile/:steamid/weapons" element={<WeaponsView />} />
              <Route path="/match/:matchId" element={<MatchDetailView />} />
              <Route path="/settings" element={<SettingsView />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </div>
    </UserContext.Provider>
  );
}
