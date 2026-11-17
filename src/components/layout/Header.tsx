import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  CircleUser,
  LifeBuoy,
  LogOut,
  Menu,
  Moon,
  Search,
  Settings,
  Sparkles,
  Sun } from
'lucide-react';
import { cn } from '../../utils/cn';
import { routeTitles } from '../../data/navigation';
import { notifications as seedNotifications } from '../../data/ai';
import { formatRelative, initialsOf } from '../../utils/format';
import { useTheme } from '../../contexts/ThemeContext';
import { ROLE_LABEL, useAuth, useCurrentUser } from '../../contexts/AuthContext';
import { Button } from '../ui/Button';
import { Dropdown, DropdownItem, DropdownLabel, DropdownSeparator } from '../ui/Dropdown';
import { Kbd } from '../ui/Controls';
import { Badge } from '../ui/Badge';
import { Tooltip } from '../ui/Tooltip';

const kindTone = {
  risk: 'bg-risk-critical',
  compliance: 'bg-primary',
  ai: 'bg-ai',
  system: 'bg-muted-foreground'
} as const;

/** Says plainly that figures come from stored data (finding F8): there is no live monitoring to signal. */
export function MonitoringStatus({ compact = false }: {compact?: boolean;}) {
  return (
    <span
      className="flex items-center gap-2 rounded-md border border-border px-2 py-1"
      title="Figures are computed from data already stored. Nothing here watches events as they happen."
      role="status">
      
      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" aria-hidden />
      <span className="font-mono text-[10px] font-semibold uppercase tracking-label text-muted-foreground">
        {compact ? 'Stored data' : 'Retrospective analysis'}
      </span>
    </span>);

}

export function Header({
  onOpenCommand,
  onOpenMobileNav



}: {onOpenCommand: () => void;onOpenMobileNav: () => void;}) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { signOut } = useAuth();
  const user = useCurrentUser();
  const roleLabel = ROLE_LABEL[user.role] ?? user.role;
  const [items, setItems] = useState(seedNotifications);
  const unread = items.filter((n) => !n.read).length;
  const title = routeTitles[pathname] ?? 'Sentinel AI';

  return (
    <header className="glass sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border px-3 lg:px-5">
      <Button
        variant="ghost"
        size="icon-sm"
        className="lg:hidden"
        onClick={onOpenMobileNav}
        aria-label="Open navigation">
        
        <Menu className="h-4 w-4" />
      </Button>

      <div className="flex min-w-0 items-center gap-2.5">
        <span
          className="hidden h-1.5 w-1.5 rounded-full bg-primary sm:block"
          aria-hidden />
        
        <h1 className="truncate text-[13px] font-semibold uppercase tracking-label">
          {title}
        </h1>
        <span className="hidden font-mono text-2xs text-muted-foreground md:inline">
          / northwind-financial
        </span>
      </div>

      <div className="flex-1" />

      <div className="hidden xl:block">
        <MonitoringStatus />
      </div>

      {/* Global search / command palette */}
      <button
        type="button"
        onClick={onOpenCommand}
        className="hidden h-8 w-56 items-center gap-2.5 rounded-md border border-border bg-surface-1/70 px-2.5 text-left text-[13px] text-muted-foreground transition-colors duration-180 hover:border-primary/40 hover:text-foreground md:flex xl:w-72">
        
        <Search className="h-3.5 w-3.5 shrink-0" aria-hidden />
        <span className="flex-1 truncate">Search everything...</span>
        <Kbd>⌘K</Kbd>
      </button>
      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden"
        onClick={onOpenCommand}
        aria-label="Search">
        
        <Search className="h-4 w-4" />
      </Button>

      <Button
        variant="ai"
        size="sm"
        onClick={() => navigate('/copilot')}
        iconLeft={<Sparkles className="h-3.5 w-3.5" />}
        className="hidden sm:inline-flex">
        
        AI Copilot
      </Button>

      <Tooltip label={theme === 'dark' ? 'Light mode' : 'Dark mode'}>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </Tooltip>

      {/* Notifications */}
      <Dropdown
        label="Notifications"
        menuClassName="w-[340px] p-0"
        trigger={({ toggle }) =>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggle}
          aria-label={`Notifications, ${unread} unread`}
          className="relative">
          
            <Bell className="h-4 w-4" />
            {unread > 0 &&
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-risk-critical ring-2 ring-background" />
          }
          </Button>
        }>
        
        <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
          <p className="text-[13px] font-semibold">Signals</p>
          <button
            type="button"
            onClick={() => setItems((n) => n.map((i) => ({ ...i, read: true })))}
            className="text-2xs font-medium text-primary hover:underline">
            
            Mark all read
          </button>
        </div>
        <ul className="max-h-80 overflow-y-auto p-1.5">
          {items.map((item) =>
          <li key={item.id}>
              <button
              type="button"
              onClick={() =>
              setItems((n) =>
              n.map((i) => i.id === item.id ? { ...i, read: true } : i)
              )
              }
              className="flex w-full gap-2.5 rounded-md px-2.5 py-2.5 text-left transition-colors hover:bg-accent">
              
                <span
                className={cn(
                  'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                  kindTone[item.kind],
                  item.read && 'opacity-30'
                )}
                aria-hidden />
              
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span
                    className={cn(
                      'truncate text-[13px]',
                      item.read ? 'font-medium text-muted-foreground' : 'font-semibold'
                    )}>
                    
                      {item.title}
                    </span>
                    <span className="shrink-0 font-mono text-2xs text-muted-foreground">
                      {formatRelative(item.createdAt)}
                    </span>
                  </span>
                  <span className="mt-0.5 line-clamp-2 block text-xs text-muted-foreground">
                    {item.body}
                  </span>
                </span>
              </button>
            </li>
          )}
        </ul>
      </Dropdown>

      {/* Profile */}
      <Dropdown
        label="Account"
        trigger={({ toggle }) =>
        <button
          type="button"
          onClick={toggle}
          aria-label="Account menu"
          className="flex items-center gap-2 rounded-md p-0.5 pr-1 transition-colors duration-180 hover:bg-accent">
          
            <span className="flex h-6 w-6 items-center justify-center rounded bg-primary/15 text-[10px] font-semibold text-primary">
              {initialsOf(user.full_name)}
            </span>
            <span className="hidden text-left lg:block">
              <span className="block text-2xs font-medium leading-tight">{user.full_name}</span>
              <span className="block text-[10px] leading-tight text-muted-foreground">
                {roleLabel}
              </span>
            </span>
          </button>
        }>
        
        {(close) =>
        <>
            <div className="px-2.5 py-2">
              <p className="text-[13px] font-semibold">{user.full_name}</p>
              <p className="text-2xs text-muted-foreground">{user.email}</p>
              <Badge tone="primary" className="mt-2">
                {roleLabel}
              </Badge>
            </div>
            <DropdownSeparator />
            <DropdownLabel>Account</DropdownLabel>
            <DropdownItem
            icon={<CircleUser className="h-4 w-4" />}
            onClick={() => {
              navigate('/profile');
              close();
            }}>
            
              Profile
            </DropdownItem>
            <DropdownItem
            icon={<Settings className="h-4 w-4" />}
            onClick={() => {
              navigate('/settings');
              close();
            }}>
            
              Workspace settings
            </DropdownItem>
            <DropdownItem icon={<LifeBuoy className="h-4 w-4" />} onClick={close}>
              Support & SLA
            </DropdownItem>
            <DropdownSeparator />
            <DropdownItem
            destructive
            icon={<LogOut className="h-4 w-4" />}
            onClick={() => {
              close();
              void signOut();
            }}>
            
              Sign out
            </DropdownItem>
          </>
        }
      </Dropdown>
    </header>);

}