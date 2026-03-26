import { useEffect, useRef, useState } from 'react';
import { ChevronDown, User, Check, Zap } from 'lucide-react';
import { clsx } from 'clsx';
import { useAccounts } from '@/hooks/useAccounts';
import { useAccountStore } from '@/stores/accountStore';

/**
 * Account switcher dropdown shown at the top of the sidebar.
 * Sets the globally selected account ID in the store.
 * All data hooks automatically re-fetch for the selected account.
 */
export function AccountSwitcher() {
  const { data: accounts = [], isLoading } = useAccounts();
  const { selectedAccountId, setSelectedAccountId } = useAccountStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Auto-select default account if nothing is selected yet
  useEffect(() => {
    if (accounts.length > 0 && selectedAccountId === null) {
      const def = accounts.find((a) => a.is_default) ?? accounts[0];
      setSelectedAccountId(def.id);
    }
  }, [accounts, selectedAccountId, setSelectedAccountId]);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = accounts.find((a) => a.id === selectedAccountId);
  const displayName = selected?.name ?? (isLoading ? '...' : 'Select account');

  return (
    <div ref={ref} className="relative px-2 mb-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
        disabled={isLoading}
      >
        <User size={16} className="shrink-0 text-gray-500 dark:text-gray-400" />
        <span className="flex-1 text-left truncate font-medium text-gray-700 dark:text-gray-200">
          {displayName}
        </span>
        {selected?.automation_enabled && (
          <Zap size={13} className="shrink-0 text-green-500" />
        )}
        <ChevronDown
          size={14}
          className={clsx(
            'shrink-0 text-gray-400 transition-transform',
            open && 'rotate-180'
          )}
        />
      </button>

      {open && accounts.length > 0 && (
        <ul className="absolute left-2 right-2 top-full mt-1 z-50 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg py-1">
          {accounts.map((account) => (
            <li key={account.id}>
              <button
                onClick={() => {
                  setSelectedAccountId(account.id);
                  setOpen(false);
                }}
                className={clsx(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                  account.id === selectedAccountId
                    ? 'text-white bg-primary-light dark:bg-primary-dark'
                    : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                )}
              >
                <span className="flex-1 text-left truncate">{account.name}</span>
                {account.automation_enabled && (
                  <Zap size={12} className={clsx(
                    account.id === selectedAccountId ? 'text-white' : 'text-green-500'
                  )} />
                )}
                {!account.has_credentials && (
                  <span className={clsx(
                    'text-xs',
                    account.id === selectedAccountId ? 'text-white/70' : 'text-gray-400'
                  )}>
                    no creds
                  </span>
                )}
                {account.id === selectedAccountId && (
                  <Check size={14} />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
