import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import {
  Plus,
  Trash2,
  Star,
  Play,
  Square,
  Key,
  KeyRound,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Pencil,
  Check,
  X,
  Settings2,
} from 'lucide-react';
import { clsx } from 'clsx';
import { Toggle, Input } from '@/components/common';
import {
  useAccounts,
  useAccount,
  useCreateAccount,
  useDeleteAccount,
  useSetDefaultAccount,
  useSetAccountCredentials,
  useClearAccountCredentials,
  useTestAccountSession,
  useStartAccountAutomation,
  useStopAccountAutomation,
  useUpdateAccount,
} from '@/hooks/useAccounts';
import { useAccountStore } from '@/stores/accountStore';
import { showSuccess, showError } from '@/stores/uiStore';
import type { Account, AccountListItem } from '@/types';

// ─── Create Account Form ────────────────────────────────────────────────────

function CreateAccountForm({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('');
  const [phpsessid, setPhpsessid] = useState('');
  const createAccount = useCreateAccount();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createAccount.mutateAsync({
        name: name.trim(),
        phpsessid: phpsessid.trim() || undefined,
      });
      showSuccess(`Account "${name}" created`);
      onClose();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create account');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50 space-y-3">
      <h3 className="font-semibold text-gray-800 dark:text-gray-100">New account</h3>
      <div>
        <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Name *</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light"
          placeholder="e.g. Main, Alt"
          required
        />
      </div>
      <div>
        <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">PHPSESSID (optional)</label>
        <input
          type="password"
          value={phpsessid}
          onChange={(e) => setPhpsessid(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light font-mono"
          placeholder="Can be set later"
        />
      </div>
      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={createAccount.isPending || !name.trim()}
          className="px-4 py-2 rounded-lg bg-primary-light dark:bg-primary-dark text-white text-sm disabled:opacity-50 flex items-center gap-2"
        >
          {createAccount.isPending && <Loader2 size={14} className="animate-spin" />}
          Create
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ─── Credentials Form ───────────────────────────────────────────────────────

function CredentialsForm({ accountId, currentUserAgent, onClose }: { accountId: number; currentUserAgent?: string; onClose: () => void }) {
  const [phpsessid, setPhpsessid] = useState('');
  const [userAgent, setUserAgent] = useState(currentUserAgent ?? '');
  const setCredentials = useSetAccountCredentials(accountId);
  const testSession = useTestAccountSession(accountId);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await setCredentials.mutateAsync({
        phpsessid: phpsessid.trim(),
        user_agent: userAgent.trim() || undefined,
      });
      showSuccess('Credentials saved');
      onClose();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save credentials');
    }
  }

  async function handleTest() {
    try {
      const result = await testSession.mutateAsync();
      if (result.valid) {
        showSuccess(`Session valid — ${result.username ?? 'unknown'} (${result.points ?? '?'} pts)`);
      } else {
        showError(`Session invalid: ${result.error ?? 'unknown error'}`);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Test failed');
    }
  }

  return (
    <form onSubmit={handleSave} className="mt-3 space-y-2 pl-4 border-l-2 border-primary-light/30">
      <div>
        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">New PHPSESSID</label>
        <input
          type="password"
          value={phpsessid}
          onChange={(e) => setPhpsessid(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-light"
          placeholder="Paste your PHPSESSID here"
          required
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">User Agent (optional)</label>
        <input
          type="text"
          value={userAgent}
          onChange={(e) => setUserAgent(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light"
          placeholder="Leave empty to use default"
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={setCredentials.isPending || !phpsessid.trim()}
          className="px-3 py-1.5 rounded-lg bg-primary-light dark:bg-primary-dark text-white text-xs disabled:opacity-50 flex items-center gap-1"
        >
          {setCredentials.isPending && <Loader2 size={12} className="animate-spin" />}
          Save
        </button>
        <button
          type="button"
          onClick={handleTest}
          disabled={testSession.isPending}
          className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-1"
        >
          {testSession.isPending ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          Test current
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ─── Account Settings Panel ─────────────────────────────────────────────────

type SettingsForm = Pick<
  Account,
  | 'dlc_enabled'
  | 'safety_check_enabled'
  | 'auto_hide_unsafe'
  | 'autojoin_enabled'
  | 'autojoin_start_at'
  | 'autojoin_stop_at'
  | 'autojoin_min_price'
  | 'autojoin_min_score'
  | 'autojoin_min_reviews'
  | 'autojoin_max_game_age'
  | 'scan_interval_minutes'
  | 'max_scan_pages'
  | 'max_entries_per_cycle'
  | 'entry_delay_min'
  | 'entry_delay_max'
>;

function SectionHeader({ title }: { title: string }) {
  return (
    <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mt-4 mb-2">
      {title}
    </p>
  );
}

function AccountSettingsPanel({ accountId }: { accountId: number }) {
  const { data: account, isLoading } = useAccount(accountId);
  const updateAccount = useUpdateAccount(accountId);
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (account) {
      setForm({
        dlc_enabled: account.dlc_enabled,
        safety_check_enabled: account.safety_check_enabled,
        auto_hide_unsafe: account.auto_hide_unsafe,
        autojoin_enabled: account.autojoin_enabled,
        autojoin_start_at: account.autojoin_start_at,
        autojoin_stop_at: account.autojoin_stop_at,
        autojoin_min_price: account.autojoin_min_price,
        autojoin_min_score: account.autojoin_min_score,
        autojoin_min_reviews: account.autojoin_min_reviews,
        autojoin_max_game_age: account.autojoin_max_game_age,
        scan_interval_minutes: account.scan_interval_minutes,
        max_scan_pages: account.max_scan_pages,
        max_entries_per_cycle: account.max_entries_per_cycle,
        entry_delay_min: account.entry_delay_min,
        entry_delay_max: account.entry_delay_max,
      });
      setHasChanges(false);
    }
  }, [account]);

  function set<K extends keyof SettingsForm>(field: K, value: SettingsForm[K]) {
    setForm((prev) => prev ? { ...prev, [field]: value } : prev);
    setHasChanges(true);
  }

  async function handleSave() {
    if (!form) return;
    try {
      await updateAccount.mutateAsync(form);
      showSuccess('Settings saved');
      setHasChanges(false);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to save settings');
    }
  }

  if (isLoading || !form) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 py-2">
        <Loader2 size={12} className="animate-spin" />
        Loading settings…
      </div>
    );
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 pt-3 space-y-1">
      {/* Automation */}
      <SectionHeader title="Automation" />
      <Toggle
        label="Include DLC"
        description="Scan and enter giveaways for DLC content"
        checked={form.dlc_enabled}
        onChange={(v) => set('dlc_enabled', v)}
      />
      <Toggle
        label="Enable Auto-Join"
        description="Automatically enter eligible giveaways"
        checked={form.autojoin_enabled}
        onChange={(v) => set('autojoin_enabled', v)}
      />

      {/* Safety */}
      <SectionHeader title="Safety" />
      <Toggle
        label="Trap Detection"
        description="Check giveaways for warning words before auto-entering"
        checked={form.safety_check_enabled}
        onChange={(v) => set('safety_check_enabled', v)}
      />
      <Toggle
        label="Auto-Hide Unsafe"
        description="Automatically hide detected trap giveaways on SteamGifts"
        checked={form.auto_hide_unsafe}
        onChange={(v) => set('auto_hide_unsafe', v)}
      />

      {/* Auto-Join Rules */}
      <SectionHeader title="Auto-Join Rules" />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Start at Points"
          type="number"
          value={form.autojoin_start_at}
          onChange={(e) => set('autojoin_start_at', parseInt(e.target.value) || 0)}
          helperText="Auto-join when points ≥ this"
        />
        <Input
          label="Stop at Points"
          type="number"
          value={form.autojoin_stop_at}
          onChange={(e) => set('autojoin_stop_at', parseInt(e.target.value) || 0)}
          helperText="Stop when points drop below this"
        />
        <Input
          label="Min Game Price ($)"
          type="number"
          value={form.autojoin_min_price}
          onChange={(e) => set('autojoin_min_price', parseInt(e.target.value) || 0)}
          helperText="Minimum game price"
        />
        <Input
          label="Min Review Score"
          type="number"
          value={form.autojoin_min_score}
          onChange={(e) => set('autojoin_min_score', parseInt(e.target.value) || 0)}
          helperText="Score 0–10"
        />
        <Input
          label="Min Review Count"
          type="number"
          value={form.autojoin_min_reviews}
          onChange={(e) => set('autojoin_min_reviews', parseInt(e.target.value) || 0)}
          helperText="Minimum Steam reviews"
        />
        <Input
          label="Max Game Age (years)"
          type="number"
          value={form.autojoin_max_game_age ?? ''}
          onChange={(e) => set('autojoin_max_game_age', e.target.value ? parseInt(e.target.value) : null)}
          helperText="Empty = no limit"
        />
      </div>

      {/* Scheduler */}
      <SectionHeader title="Scheduler" />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Scan Interval (min)"
          type="number"
          value={form.scan_interval_minutes}
          onChange={(e) => set('scan_interval_minutes', parseInt(e.target.value) || 30)}
          helperText="How often to scan"
        />
        <Input
          label="Max Scan Pages"
          type="number"
          value={form.max_scan_pages}
          onChange={(e) => set('max_scan_pages', parseInt(e.target.value) || 3)}
          helperText="Pages per cycle"
        />
        <Input
          label="Max Entries / Cycle"
          type="number"
          value={form.max_entries_per_cycle ?? ''}
          onChange={(e) => set('max_entries_per_cycle', e.target.value ? parseInt(e.target.value) : null)}
          helperText="Empty = unlimited"
        />
      </div>

      {/* Rate Limiting */}
      <SectionHeader title="Rate Limiting" />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Min Delay (sec)"
          type="number"
          value={form.entry_delay_min}
          onChange={(e) => set('entry_delay_min', parseInt(e.target.value) || 0)}
          helperText="Min delay between entries"
        />
        <Input
          label="Max Delay (sec)"
          type="number"
          value={form.entry_delay_max}
          onChange={(e) => set('entry_delay_max', parseInt(e.target.value) || 0)}
          helperText="Max delay between entries"
        />
      </div>

      {/* Save */}
      {hasChanges && (
        <div className="flex justify-end pt-3">
          <button
            onClick={handleSave}
            disabled={updateAccount.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-light dark:bg-primary-dark text-white text-sm disabled:opacity-50"
          >
            {updateAccount.isPending && <Loader2 size={14} className="animate-spin" />}
            Save settings
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Account Row ────────────────────────────────────────────────────────────

function AccountRow({ account, defaultOpen = false }: { account: AccountListItem; defaultOpen?: boolean }) {
  const [expanded, setExpanded] = useState(defaultOpen);
  const [showCredentials, setShowCredentials] = useState(defaultOpen);
  const [showSettings, setShowSettings] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(account.name);
  const { selectedAccountId, setSelectedAccountId } = useAccountStore();

  const deleteAccount = useDeleteAccount();
  const setDefault = useSetDefaultAccount();
  const clearCredentials = useClearAccountCredentials(account.id);
  const startAutomation = useStartAccountAutomation();
  const stopAutomation = useStopAccountAutomation();
  const testSession = useTestAccountSession(account.id);
  const updateAccount = useUpdateAccount(account.id);

  async function handleDelete() {
    if (!confirm(`Delete account "${account.name}"? This is a soft delete (data is kept).`)) return;
    try {
      await deleteAccount.mutateAsync(account.id);
      if (selectedAccountId === account.id) setSelectedAccountId(null);
      showSuccess(`Account "${account.name}" deleted`);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to delete account');
    }
  }

  async function handleSetDefault() {
    try {
      await setDefault.mutateAsync(account.id);
      showSuccess(`"${account.name}" set as default`);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to set default');
    }
  }

  async function handleClearCredentials() {
    if (!confirm('Clear credentials for this account?')) return;
    try {
      await clearCredentials.mutateAsync();
      showSuccess('Credentials cleared');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to clear credentials');
    }
  }

  async function handleToggleAutomation() {
    try {
      if (account.automation_enabled) {
        await stopAutomation.mutateAsync(account.id);
        showSuccess(`Automation stopped for "${account.name}"`);
      } else {
        if (!account.has_credentials) {
          showError('Set credentials before starting automation');
          return;
        }
        await startAutomation.mutateAsync(account.id);
        showSuccess(`Automation started for "${account.name}"`);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to toggle automation');
    }
  }

  async function handleTestSession() {
    try {
      const result = await testSession.mutateAsync();
      if (result.valid) {
        showSuccess(`Valid — ${result.username ?? 'unknown'} (${result.points ?? '?'} pts)`);
      } else {
        showError(`Invalid session: ${result.error ?? 'unknown error'}`);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Test failed');
    }
  }

  async function handleRenameConfirm() {
    const trimmed = renameValue.trim();
    if (!trimmed || trimmed === account.name) {
      setIsRenaming(false);
      setRenameValue(account.name);
      return;
    }
    try {
      await updateAccount.mutateAsync({ name: trimmed });
      showSuccess(`Account renamed to "${trimmed}"`);
      setIsRenaming(false);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to rename account');
    }
  }

  function handleRenameKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleRenameConfirm();
    if (e.key === 'Escape') {
      setIsRenaming(false);
      setRenameValue(account.name);
    }
  }

  const isSelected = selectedAccountId === account.id;
  const automationBusy = startAutomation.isPending || stopAutomation.isPending;

  return (
    <div
      className={clsx(
        'border rounded-lg overflow-hidden transition-colors',
        isSelected
          ? 'border-primary-light dark:border-primary-dark'
          : 'border-gray-200 dark:border-gray-700'
      )}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-800">
        {/* Select button */}
        <button
          onClick={() => setSelectedAccountId(account.id)}
          className={clsx(
            'w-4 h-4 rounded-full border-2 shrink-0 transition-colors',
            isSelected
              ? 'border-primary-light dark:border-primary-dark bg-primary-light dark:bg-primary-dark'
              : 'border-gray-400 dark:border-gray-500 hover:border-primary-light'
          )}
          title="Select this account for the dashboard"
        />

        {/* Name + badges */}
        <div className="flex-1 min-w-0">
          {isRenaming ? (
            <div className="flex items-center gap-1">
              <input
                autoFocus
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onKeyDown={handleRenameKeyDown}
                className="px-2 py-0.5 rounded border border-primary-light dark:border-primary-dark bg-white dark:bg-gray-700 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-light w-40"
              />
              <button
                onClick={handleRenameConfirm}
                disabled={updateAccount.isPending}
                className="p-0.5 text-green-500 hover:text-green-600"
                title="Confirm rename"
              >
                {updateAccount.isPending ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              </button>
              <button
                onClick={() => { setIsRenaming(false); setRenameValue(account.name); }}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                title="Cancel"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-gray-800 dark:text-gray-100 truncate">
                {account.name}
              </span>
              <button
                onClick={() => { setIsRenaming(true); setRenameValue(account.name); }}
                className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                title="Rename account"
              >
                <Pencil size={12} />
              </button>
              {account.is_default && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
                  default
                </span>
              )}
              {account.autojoin_enabled && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
                  auto-join
                </span>
              )}
              {account.automation_enabled ? (
                <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  running
                </span>
              ) : (
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                  stopped
                </span>
              )}
              {!account.has_credentials && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300">
                  no credentials
                </span>
              )}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleToggleAutomation}
            disabled={automationBusy}
            title={account.automation_enabled ? 'Stop automation' : 'Start automation'}
            className={clsx(
              'p-1.5 rounded-lg transition-colors',
              account.automation_enabled
                ? 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                : 'text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
            )}
          >
            {automationBusy
              ? <Loader2 size={16} className="animate-spin" />
              : account.automation_enabled
                ? <Square size={16} />
                : <Play size={16} />
            }
          </button>

          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {!account.is_default && (
              <button
                onClick={handleSetDefault}
                disabled={setDefault.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <Star size={13} />
                Set as default
              </button>
            )}

            <button
              onClick={() => { setShowCredentials((v) => !v); setShowSettings(false); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Key size={13} />
              {showCredentials ? 'Hide credentials' : 'Set credentials'}
            </button>

            {account.has_credentials && (
              <>
                <button
                  onClick={handleTestSession}
                  disabled={testSession.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {testSession.isPending
                    ? <Loader2 size={13} className="animate-spin" />
                    : <CheckCircle size={13} />
                  }
                  Test session
                </button>

                <button
                  onClick={handleClearCredentials}
                  disabled={clearCredentials.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-200 dark:border-red-800 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <KeyRound size={13} />
                  Clear credentials
                </button>
              </>
            )}

            <button
              onClick={() => { setShowSettings((v) => !v); setShowCredentials(false); }}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-colors',
                showSettings
                  ? 'border-primary-light dark:border-primary-dark text-primary-light dark:text-primary-dark bg-primary-light/5'
                  : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
            >
              <Settings2 size={13} />
              {showSettings ? 'Hide settings' : 'Settings'}
            </button>

            <button
              onClick={handleDelete}
              disabled={deleteAccount.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-200 dark:border-red-800 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 ml-auto"
            >
              {deleteAccount.isPending
                ? <Loader2 size={13} className="animate-spin" />
                : <Trash2 size={13} />
              }
              Delete
            </button>
          </div>

          {/* Test result */}
          {testSession.data && (
            <div className={clsx(
              'flex items-center gap-2 text-sm px-3 py-2 rounded-lg',
              testSession.data.valid
                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
            )}>
              {testSession.data.valid
                ? <CheckCircle size={14} />
                : <XCircle size={14} />
              }
              {testSession.data.valid
                ? `${testSession.data.username ?? 'unknown'} — ${testSession.data.points ?? '?'} points`
                : testSession.data.error ?? 'Invalid session'
              }
            </div>
          )}

          {/* Credentials form */}
          {showCredentials && (
            <CredentialsForm
              accountId={account.id}
              onClose={() => setShowCredentials(false)}
            />
          )}

          {/* Settings panel */}
          {showSettings && <AccountSettingsPanel accountId={account.id} />}
        </div>
      )}
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export function Accounts() {
  const { data: accounts = [], isLoading, error } = useAccounts();
  const [showCreate, setShowCreate] = useState(false);
  const [searchParams] = useSearchParams();
  const setupMode = searchParams.get('setup') === 'true';

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Accounts</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage multiple SteamGifts accounts
          </p>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-light dark:bg-primary-dark text-white text-sm hover:opacity-90 transition-opacity"
        >
          <Plus size={16} />
          Add account
        </button>
      </div>

      {showCreate && (
        <div className="mb-4">
          <CreateAccountForm onClose={() => setShowCreate(false)} />
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 py-8 justify-center">
          <Loader2 size={18} className="animate-spin" />
          <span>Loading accounts…</span>
        </div>
      )}

      {error && (
        <div className="text-red-500 py-4 text-sm">
          Failed to load accounts: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      )}

      <div className="space-y-3">
        {accounts.map((account) => (
          <AccountRow
            key={account.id}
            account={account}
            defaultOpen={setupMode && account.is_default}
          />
        ))}
      </div>

      {!isLoading && accounts.length === 0 && !showCreate && (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <p>No accounts yet. Click "Add account" to get started.</p>
        </div>
      )}
    </div>
  );
}
