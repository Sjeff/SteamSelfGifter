// Account hooks
export {
  useAccounts,
  useAccount,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useSetDefaultAccount,
  useSetAccountCredentials,
  useClearAccountCredentials,
  useTestAccountSession,
  useStartAccountAutomation,
  useStopAccountAutomation,
  accountKeys,
} from "./useAccounts";

// Settings hooks
export {
  useSettings,
  useUpdateSettings,
  useValidateConfig,
  useTestSession,
  settingsKeys,
} from "./useSettings";

// Scheduler hooks
export {
  useSchedulerStatus,
  useStartScheduler,
  useStopScheduler,
  usePauseScheduler,
  useResumeScheduler,
  useTriggerScan,
  useTriggerProcess,
  useSchedulerControl,
  schedulerKeys,
} from "./useScheduler";

// Giveaway hooks
export {
  useGiveaways,
  useInfiniteGiveaways,
  useEnterGiveaway,
  useHideGiveaway,
  useUnhideGiveaway,
  useRemoveEntry,
  useCheckGiveawaySafety,
  useHideOnSteamGifts,
  usePostComment,
  giveawayKeys,
  type GiveawayFilters,
} from "./useGiveaways";

// Entry hooks
export { useEntries, entryKeys, type EntryFilters } from "./useEntries";

// Analytics hooks
export {
  useDashboard,
  useEntryStats,
  useGiveawayStats,
  useGameStats,
  useEntryTrends,
  analyticsKeys,
  type TimeRangeFilter,
  type TrendDataPoint,
} from "./useAnalytics";

// Log hooks
export {
  useLogs,
  useClearLogs,
  useExportLogs,
  logKeys,
  type LogFilters,
} from "./useLogs";

// WebSocket hooks
export {
  useWebSocket,
  useWebSocketConnection,
  useWebSocketEvent,
  useWebSocketNotifications,
  useWebSocketQueryInvalidation,
  useScanProgress,
} from "./useWebSocket";

// WebSocket status hook (for accessing provider context)
export { useWebSocketStatus } from "./useWebSocketStatus";

// Auth hooks
export {
  useAuthStatus,
  useCurrentUser,
  useSetup,
  useLogin,
  useLogout,
  useChangePassword,
  authKeys,
  type AuthUser,
  type AuthStatus,
} from "./useAuth";
