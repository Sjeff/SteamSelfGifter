import { type ReactNode } from "react";
import { useAuthStatus, useCurrentUser } from "@/hooks/useAuth";
import { Loading } from "@/components/common";
import { Login } from "@/pages/Login";
import { AuthContext } from "./AuthContext";

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Gates the whole app behind login. Renders the setup wizard or login form
 * until a valid session exists, then renders children (the routed app).
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const { data: status, isLoading: statusLoading } = useAuthStatus();
  const { data: user, isLoading: userLoading, isFetched } = useCurrentUser();

  const isLoading = statusLoading || userLoading || !isFetched;

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loading text="Loading..." />
      </div>
    );
  }

  if (!status?.setup_complete || !user) {
    return <Login setupComplete={status?.setup_complete ?? false} />;
  }

  return (
    <AuthContext.Provider
      value={{ user, isLoading: false, setupComplete: true }}
    >
      {children}
    </AuthContext.Provider>
  );
}
