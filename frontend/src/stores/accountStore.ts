import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AccountState {
  selectedAccountId: number | null;
  setSelectedAccountId: (id: number | null) => void;
}

/**
 * Account selection store
 *
 * Persists the currently selected account ID across page reloads.
 * null = use default account (backend decides).
 */
export const useAccountStore = create<AccountState>()(
  persist(
    (set) => ({
      selectedAccountId: null,
      setSelectedAccountId: (id) => set({ selectedAccountId: id }),
    }),
    { name: 'account-store' }
  )
);
