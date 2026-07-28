import { createContext, useContext } from "react";
import type { User } from "../types";

// Nunca null en tiempo de render de las vistas: App.tsx no monta <Routes>
// hasta que getMe() resuelve un usuario logueado.
export const UserContext = createContext<User | null>(null);

export function useUser(): User {
  const user = useContext(UserContext);
  if (!user) throw new Error("useUser() usado fuera de un usuario autenticado");
  return user;
}

// Setter directo (no un refetch): lo usan los settings que ya reciben el
// User actualizado como respuesta del PATCH/DELETE (ver setCustomBackground),
// para no tener que pegarle de nuevo a /auth/me.
export const UserUpdateContext = createContext<((user: User) => void) | null>(null);

export function useUpdateUser(): (user: User) => void {
  const update = useContext(UserUpdateContext);
  if (!update) throw new Error("useUpdateUser() usado fuera de un usuario autenticado");
  return update;
}
