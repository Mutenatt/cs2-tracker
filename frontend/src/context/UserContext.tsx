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
