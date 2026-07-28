import { useEffect, useRef, useState } from "react";
import { Link, NavLink } from "react-router-dom";
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
          {isActive && (
            <motion.span
              className="cs-nav-active-bg"
              layoutId="nav-active-bg"
              transition={{ type: "spring", stiffness: 500, damping: 40 }}
            />
          )}
          <span className="cs-nav-tab-label">{label}</span>
        </>
      )}
    </NavLink>
  );
}

function UserMenu({ onLogout }: { onLogout: () => void }) {
  const user = useUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div className="user-chip" ref={ref}>
      <button
        type="button"
        className="user-chip-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-label="Cuenta"
      >
        {user.avatar_url ? (
          <img className="av" src={user.avatar_url} alt="" width={28} height={28} />
        ) : (
          <span className="av" />
        )}
      </button>
      {open && (
        <div className="user-chip-menu">
          <span className="name">{user.display_name ?? user.steamid}</span>
          <button className="logout-btn" onClick={onLogout}>
            Salir
          </button>
        </div>
      )}
    </div>
  );
}

export function Topbar({ onLogout }: { onLogout: () => void }) {
  const user = useUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <>
      <div className="topbar">
        <Logo />
        <div className="live">
          <motion.span className="dot" variants={livePulse} animate="pulse" />
          <span>Datos en vivo</span>
        </div>
        <UserMenu onLogout={onLogout} />
        <div className="user-chip" ref={ref}>
          <button type="button" className="user-chip-trigger" onClick={() => setOpen((o) => !o)}>
            {user.avatar_url ? (
              <img className="av" src={user.avatar_url} alt="" width={24} height={24} />
            ) : (
              <span className="av" />
            )}
            <span className="name">{user.display_name ?? user.steamid}</span>
          </button>
          {open && (
            <div className="user-chip-menu">
              <Link className="user-chip-menu-item" to="/settings" onClick={() => setOpen(false)}>
                Configuración
              </Link>
              <button type="button" className="user-chip-menu-item" onClick={onLogout}>
                Salir
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="nav-tabs">
        <NavPill to="/" end label="Inicio" />
        <NavPill to={`/profile/${user.steamid}`} label="Perfil" />
        <NavPill to="/lineups" label="Line ups" />
      </div>
    </>
  );
}
