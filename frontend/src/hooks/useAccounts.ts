import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { schedulerKeys } from '@/hooks/useScheduler';
import type { Account, AccountListItem } from '@/types';

export const accountKeys = {
  all: ['accounts'] as const,
  lists: () => [...accountKeys.all, 'list'] as const,
  list: () => [...accountKeys.lists()] as const,
  details: () => [...accountKeys.all, 'detail'] as const,
  detail: (id: number) => [...accountKeys.details(), id] as const,
};

export function useAccounts() {
  return useQuery({
    queryKey: accountKeys.list(),
    queryFn: async () => {
      const response = await api.get<AccountListItem[]>('/api/v1/accounts');
      if (!response.success) throw new Error(response.error || 'Failed to fetch accounts');
      return response.data;
    },
  });
}

export function useAccount(id: number) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: async () => {
      const response = await api.get<Account>(`/api/v1/accounts/${id}`);
      if (!response.success) throw new Error(response.error || 'Failed to fetch account');
      return response.data;
    },
    enabled: id > 0,
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; phpsessid?: string; user_agent?: string }) => {
      const response = await api.post<Account>('/api/v1/accounts', data);
      if (!response.success) throw new Error(response.error || 'Failed to create account');
      return response.data;
    },
    onSuccess: (newAccount) => {
      // Append to list without full refetch
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) => {
        const item: AccountListItem = {
          id: newAccount.id,
          name: newAccount.name,
          is_active: newAccount.is_active,
          is_default: newAccount.is_default,
          automation_enabled: newAccount.automation_enabled,
          autojoin_enabled: newAccount.autojoin_enabled,
          has_credentials: Boolean(newAccount.phpsessid),
        };
        return old ? [...old, item] : [item];
      });
    },
  });
}

export function useUpdateAccount(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Account>) => {
      const response = await api.put<Account>(`/api/v1/accounts/${id}`, data);
      if (!response.success) throw new Error(response.error || 'Failed to update account');
      return response.data;
    },
    onSuccess: (updated) => {
      // Update detail cache
      queryClient.setQueryData(accountKeys.detail(id), updated);
      // Patch the list entry with changed fields
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) =>
          a.id === id
            ? {
                ...a,
                name: updated.name,
                autojoin_enabled: updated.autojoin_enabled,
                automation_enabled: updated.automation_enabled,
                has_credentials: Boolean(updated.phpsessid),
              }
            : a
        )
      );
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete<{ deleted: boolean }>(`/api/v1/accounts/${id}`);
      if (!response.success) throw new Error(response.error || 'Failed to delete account');
      return response.data;
    },
    onSuccess: (_, id) => {
      // Remove from list immediately
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.filter((a) => a.id !== id)
      );
      queryClient.removeQueries({ queryKey: accountKeys.detail(id) });
    },
  });
}

export function useSetDefaultAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<Account>(`/api/v1/accounts/${id}/set-default`);
      if (!response.success) throw new Error(response.error || 'Failed to set default account');
      return response.data;
    },
    onSuccess: (_, id) => {
      // Toggle is_default flags in list without refetch
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) => ({ ...a, is_default: a.id === id }))
      );
    },
  });
}

export function useSetAccountCredentials(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { phpsessid: string; user_agent?: string }) => {
      const response = await api.post<Account>(`/api/v1/accounts/${id}/credentials`, data);
      if (!response.success) throw new Error(response.error || 'Failed to set credentials');
      return response.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(accountKeys.detail(id), updated);
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) => (a.id === id ? { ...a, has_credentials: true } : a))
      );
    },
  });
}

export function useClearAccountCredentials(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<Account>(`/api/v1/accounts/${id}/credentials`);
      if (!response.success) throw new Error(response.error || 'Failed to clear credentials');
      return response.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(accountKeys.detail(id), updated);
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) => (a.id === id ? { ...a, has_credentials: false } : a))
      );
    },
  });
}

export function useTestAccountSession(id: number) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<{ valid: boolean; username?: string; points?: number; error?: string }>(
        `/api/v1/accounts/${id}/test-session`
      );
      if (!response.success) throw new Error(response.error || 'Failed to test session');
      return response.data;
    },
  });
}

export function useStartAccountAutomation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<{ started: boolean; account_id: number }>(
        `/api/v1/accounts/${id}/scheduler/start`
      );
      if (!response.success) throw new Error(response.error || 'Failed to start automation');
      return response.data;
    },
    onSuccess: (_, id) => {
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) => (a.id === id ? { ...a, automation_enabled: true } : a))
      );
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

export function useStopAccountAutomation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<{ stopped: boolean; account_id: number }>(
        `/api/v1/accounts/${id}/scheduler/stop`
      );
      if (!response.success) throw new Error(response.error || 'Failed to stop automation');
      return response.data;
    },
    onSuccess: (_, id) => {
      queryClient.setQueryData(accountKeys.list(), (old: AccountListItem[] | undefined) =>
        old?.map((a) => (a.id === id ? { ...a, automation_enabled: false } : a))
      );
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}
