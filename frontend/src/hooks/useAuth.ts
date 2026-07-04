import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";

export interface AuthUser {
  id: number;
  username: string;
}

export interface AuthStatus {
  setup_complete: boolean;
}

export const authKeys = {
  all: ["auth"] as const,
  status: () => [...authKeys.all, "status"] as const,
  me: () => [...authKeys.all, "me"] as const,
};

export function useAuthStatus() {
  return useQuery({
    queryKey: authKeys.status(),
    queryFn: async () => {
      const response = await api.get<AuthStatus>("/api/v1/auth/status");
      if (!response.success) throw new Error("Failed to check setup status");
      return response.data;
    },
  });
}

/** The current user, or null if not logged in. Never throws on 401. */
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: async () => {
      const response = await api.get<AuthUser>("/api/v1/auth/me");
      return response.success ? response.data : null;
    },
    retry: false,
  });
}

export function useSetup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { username: string; password: string }) => {
      const response = await api.post<AuthUser>("/api/v1/auth/setup", body);
      if (!response.success) throw new Error("Setup failed");
      return response.data;
    },
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me(), user);
      queryClient.setQueryData(authKeys.status(), { setup_complete: true });
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { username: string; password: string }) => {
      const response = await api.post<AuthUser>("/api/v1/auth/login", body);
      if (!response.success) throw new Error("Invalid username or password");
      return response.data;
    },
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me(), user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/api/v1/auth/logout");
    },
    onSuccess: () => {
      queryClient.setQueryData(authKeys.me(), null);
      queryClient.clear();
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: {
      current_password: string;
      new_password: string;
    }) => {
      const response = await api.post("/api/v1/auth/change-password", body);
      if (!response.success) throw new Error("Current password is incorrect");
      return response.data;
    },
  });
}
