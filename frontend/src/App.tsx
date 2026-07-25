import { useEffect, useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { getMe, logout } from "./api";
import { Topbar } from "./components/Topbar";
import { ROUTE_FADE } from "./components/motion/presets";
import { UserContext } from "./context/UserContext";
import { HomeView } from "./views/HomeView";
import { LandingView } from "./views/LandingView";
import { LineUps } from "./views/LineUps";
import { MatchDetailView } from "./views/MatchDetailView";
import { ProfileView } from "./views/ProfileView";
import { WeaponsView } from "./views/WeaponsView";
import type { User } from "./types";

export function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [authError, setAuthError] = useState(false);
  const location = useLocation();

  useEffect(() => {
    (async () => {
      try {
        setUser(await getMe());
      } catch {
        setAuthError(true);
      }
    })();
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

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
  if (user === undefined) return <div className="wrap center">Cargando…</div>;
  if (user === null) return <LandingView />;

  const handleLogout = async () => {
    await logout();
    setUser(null);
  };

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
            </Routes>
          </motion.div>
        </AnimatePresence>
      </div>
    </UserContext.Provider>
  );
}
