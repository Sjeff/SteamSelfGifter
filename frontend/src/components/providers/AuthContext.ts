import { createContext } from "react";
import type { AuthUser } from "@/hooks/useAuth";

export interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  setupComplete: boolean;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  setupComplete: true,
});
