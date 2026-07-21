import { NavLink } from "react-router-dom";
import { motion } from "motion/react";
import { useUser } from "../context/UserContext";
import { Logo } from "./Logo";
import { livePulse } from "./motion/presets";

function NavPill({ to, end, label }: { to: string; end?: boolean; label: string }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => `cs-nav-tab${isActive ? " active" : ""}`}
    >
      {({ isActive }) => (
        <>
          <span className="cs-nav-tab-label">{label}</span>
          {isActive && (
            <motion.span
              className="cs-nav-underline"
              layoutId="nav-underline"
              transition={{ type: "spring", stiffness: 500, damping: 40 }}
            />
          )}
        </>
      )}
    </NavLink>
  );
}

export function Topbar({ onLogout }: { onLogout: () => void }) {
  const user = useUser();
  return (
    <>
      <div className="topbar">
        <Logo />
        <div className="live">
          <motion.span className="dot" variants={livePulse} animate="pulse" />
          <span>Datos en vivo</span>
        </div>
        <div className="user-chip">
          {user.avatar_url ? (
            <img className="av" src={user.avatar_url} alt="" width={24} height={24} />
          ) : (
            <span className="av" />
          )}
          <span className="name">{user.display_name ?? user.steamid}</span>
          <button className="logout-btn" onClick={onLogout}>
            Salir
          </button>
        </div>
      </div>
      <div className="nav-tabs">
        <NavPill to="/" end label="Inicio" />
        <span className="cs-nav-tab inert" aria-disabled="true" title="Próximamente">
          Historial
        </span>
        <span className="cs-nav-tab inert" aria-disabled="true" title="Próximamente">
          Line ups
        </span>
        <NavPill to={`/profile/${user.steamid}`} label="Perfil" />
      </div>
    </>
  );
}
