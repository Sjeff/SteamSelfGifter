import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { SchedulerStatus, ScanResult, ProcessResult, WinSyncResult, AutomationCycleResult } from '@/types';
import { useAccountStore } from '@/stores/accountStore';

/**
 * Query keys for scheduler
 */
export const schedulerKeys = {
  all: ['scheduler'] as const,
  status: ['scheduler', 'status'] as const,
};

/**
 * Fetch scheduler status, scoped to the selected account when available
 */
export function useSchedulerStatus() {
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useQuery({
    queryKey: [...schedulerKeys.status, selectedAccountId],
    queryFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/status`
        : '/api/v1/scheduler/status';
      const response = await api.get<SchedulerStatus>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch scheduler status');
      }
      return response.data;
    },
    // Refetch every 10 seconds for live status
    refetchInterval: 10_000,
  });
}

/**
 * Start the scheduler
 */
export function useStartScheduler() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/start`
        : '/api/v1/scheduler/start';
      const response = await api.post<SchedulerStatus>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to start scheduler');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Stop the scheduler
 */
export function useStopScheduler() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/stop`
        : '/api/v1/scheduler/stop';
      const response = await api.post<SchedulerStatus>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to stop scheduler');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Pause the scheduler
 */
export function usePauseScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post<SchedulerStatus>('/api/v1/scheduler/pause');
      if (!response.success) {
        throw new Error(response.error || 'Failed to pause scheduler');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Resume the scheduler
 */
export function useResumeScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post<SchedulerStatus>('/api/v1/scheduler/resume');
      if (!response.success) {
        throw new Error(response.error || 'Failed to resume scheduler');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Trigger a manual scan
 */
export function useTriggerScan() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/scan`
        : '/api/v1/scheduler/scan';
      const response = await api.post<ScanResult>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to trigger scan');
      }
      return response.data;
    },
    onSuccess: () => {
      // Invalidate giveaways since scan may find new ones
      queryClient.invalidateQueries({ queryKey: ['giveaways'] });
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Trigger auto-entry processing
 */
export function useTriggerProcess() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/process`
        : '/api/v1/scheduler/process';
      const response = await api.post<ProcessResult>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to trigger process');
      }
      return response.data;
    },
    onSuccess: () => {
      // Invalidate entries and giveaways since process creates entries
      queryClient.invalidateQueries({ queryKey: ['entries'] });
      queryClient.invalidateQueries({ queryKey: ['giveaways'] });
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Trigger win sync
 */
export function useSyncWins() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/sync-wins`
        : '/api/v1/scheduler/sync-wins';
      const response = await api.post<WinSyncResult>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to sync wins');
      }
      return response.data;
    },
    onSuccess: () => {
      // Invalidate giveaways since wins status may change
      queryClient.invalidateQueries({ queryKey: ['giveaways'] });
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Trigger a full automation cycle
 */
export function useRunAutomationCycle() {
  const queryClient = useQueryClient();
  const selectedAccountId = useAccountStore((s) => s.selectedAccountId);

  return useMutation({
    mutationFn: async () => {
      // Use account-specific endpoint if an account is selected
      const endpoint = selectedAccountId
        ? `/api/v1/accounts/${selectedAccountId}/scheduler/run`
        : '/api/v1/scheduler/run';
      const response = await api.post<AutomationCycleResult>(endpoint);
      if (!response.success) {
        throw new Error(response.error || 'Failed to run automation cycle');
      }
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all relevant queries
      queryClient.invalidateQueries({ queryKey: ['giveaways'] });
      queryClient.invalidateQueries({ queryKey: ['entries'] });
      queryClient.invalidateQueries({ queryKey: schedulerKeys.all });
    },
  });
}

/**
 * Combined scheduler control hook
 */
export function useSchedulerControl() {
  const start = useStartScheduler();
  const stop = useStopScheduler();
  const pause = usePauseScheduler();
  const resume = useResumeScheduler();
  const scan = useTriggerScan();
  const process = useTriggerProcess();
  const syncWins = useSyncWins();
  const runCycle = useRunAutomationCycle();

  return { start, stop, pause, resume, scan, process, syncWins, runCycle };
}
