import { NavLink } from 'react-router';
declare const __APP_VERSION__: string;
import {
  LayoutDashboard,
  Gift,
  Trophy,
  History,
  BarChart3,
  FileText,
  Users,
  LucideIcon,
} from 'lucide-react';
import { clsx } from 'clsx';
import { AccountSwitcher } from './AccountSwitcher';

interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

// Navigation items configuration
const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/giveaways', label: 'Giveaways', icon: Gift },
  { path: '/wins', label: 'Wins', icon: Trophy },
  { path: '/history', label: 'History', icon: History },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/accounts', label: 'Accounts', icon: Users },
  { path: '/logs', label: 'Logs', icon: FileText },
];

/**
 * Sidebar navigation component
 */
export function Sidebar() {
  return (
    <aside className="w-64 border-r border-gray-200 dark:border-gray-700 bg-surface-light dark:bg-surface-dark min-h-[calc(100vh-4rem)]">
      <nav className="p-4">
        <AccountSwitcher />
        <ul className="space-y-2">
          {navItems.map(({ path, label, icon: Icon }) => (
            <li key={path}>
              <NavLink
                to={path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary-light dark:bg-primary-dark text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  )
                }
              >
                <Icon size={20} />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <p className="mt-4 px-4 text-xs text-gray-400 dark:text-gray-500">v{__APP_VERSION__}</p>
      </nav>
    </aside>
  );
}
