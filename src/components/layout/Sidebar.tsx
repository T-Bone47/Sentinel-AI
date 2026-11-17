import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { cn } from '../../utils/cn';
import { navigation } from '../../data/navigation';
import { Tooltip } from '../ui/Tooltip';
import { useApiResource } from '../../hooks/useApiResource';
import { getDashboard } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

export function Sidebar({
  collapsed,
  onToggle,
  onNavigate,
  className





}: {collapsed: boolean;onToggle: () => void;onNavigate?: () => void;className?: string;}) {
  const { pathname } = useLocation();
  const { can } = useAuth();
  // Hide screens the signed-in role cannot read (the server would answer 403).
  const visibleNavigation = navigation.
  map((group) => ({ ...group, items: group.items.filter((item) => !item.resource || can(item.resource)) })).
  filter((group) => group.items.length > 0);
  const showTrust = can('dashboard');
  const dashboardState = useApiResource(() => showTrust ? getDashboard() : Promise.resolve(null), [showTrust]);
  const currentTrustScore = dashboardState.data?.trustScore.value ?? 0;

  return (
    <motion.nav
      aria-label="Primary"
      animate={{ width: collapsed ? 64 : 236 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'relative z-20 flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar',
        className
      )}>
      
      {/* Brand */}
      <div
        className={cn(
          'flex h-14 items-center gap-2.5 border-b border-sidebar-border px-3',
          collapsed && 'justify-center px-0'
        )}>
        
        <span className="relative flex h-7 w-7 shrink-0 items-center justify-center" aria-hidden>
          <svg viewBox="0 0 28 28" className="h-7 w-7">
            <path
              d="M14 2.5 24 6.5v8.2c0 5.4-4.1 9.9-10 11.3-5.9-1.4-10-5.9-10-11.3V6.5L14 2.5Z"
              style={{ fill: 'oklch(var(--primary) / 0.14)', stroke: 'oklch(var(--primary))' }}
              strokeWidth="1.4" />
            
            <path
              d="M9 14.2h3.1l1.6-3.4 1.8 6.4 1.5-3h3"
              fill="none"
              style={{ stroke: 'oklch(var(--cyan))' }}
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round" />
            
          </svg>
        </span>
        {!collapsed &&
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-w-0">
            <p className="truncate text-[13px] font-semibold uppercase tracking-label">
              Sentinel AI
            </p>
            <p className="truncate text-2xs text-muted-foreground">Northwind Financial</p>
          </motion.div>
        }
      </div>

      {/* Navigation */}
      <div className="scrollbar-none flex-1 overflow-y-auto px-2 py-3">
        {visibleNavigation.map((group, groupIndex) =>
        <div key={group.label} className={cn(groupIndex > 0 && 'mt-4')}>
            {collapsed ?
          groupIndex > 0 && <div className="mx-auto mb-2 h-px w-6 bg-sidebar-border" /> :

          <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-label text-muted-foreground/70">
                {group.label}
              </p>
          }
            <ul className="space-y-0.5">
              {group.items.map((item) => {
              const active =
              item.to === '/' ? pathname === '/' : pathname.startsWith(item.to);
              const link =
              <NavLink
                to={item.to}
                onClick={onNavigate}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'group relative flex items-center gap-2.5 rounded-md px-2 py-[7px] text-[13px] font-medium transition-colors duration-180',
                  collapsed && 'justify-center px-0',
                  active ?
                  item.tone === 'ai' ?
                  'text-ai' :
                  'text-foreground' :
                  'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                )}>
                
                    {active &&
                <motion.span
                  layoutId="nav-active"
                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                  className={cn(
                    'absolute inset-0 rounded-md border',
                    item.tone === 'ai' ?
                    'border-ai-border/60 bg-ai/[0.10]' :
                    'border-primary/35 bg-primary/[0.10]'
                  )} />

                }
                    {active &&
                <span
                  className={cn(
                    'absolute -left-2 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full',
                    item.tone === 'ai' ? 'bg-ai' : 'bg-primary glow-primary'
                  )}
                  aria-hidden />

                }
                    <item.icon
                  className={cn(
                    'relative h-[17px] w-[17px] shrink-0',
                    active && item.tone === 'ai' && 'text-ai',
                    active && item.tone !== 'ai' && 'text-primary'
                  )}
                  aria-hidden />
                
                    {!collapsed &&
                <>
                        <span className="relative flex-1 truncate">{item.label}</span>
                        {(item.to === '/risk' ? (dashboardState.data?.raw.risks.open ? String(dashboardState.data.raw.risks.open) : item.badge) : 
                          item.to === '/findings' ? (dashboardState.data?.raw.findings.open ? String(dashboardState.data.raw.findings.open) : item.badge) : 
                          item.badge) &&
                  <span
                    className={cn(
                      'relative rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold',
                      item.tone === 'critical' || (item.to === '/risk' && dashboardState.data?.raw.risks.critical && dashboardState.data.raw.risks.critical > 0) ?
                      'bg-risk-critical/15 text-risk-critical' :
                      'bg-muted text-muted-foreground'
                    )}>
                    
                            {item.to === '/risk' ? (dashboardState.data?.raw.risks.open ? String(dashboardState.data.raw.risks.open) : item.badge) : 
                             item.to === '/findings' ? (dashboardState.data?.raw.findings.open ? String(dashboardState.data.raw.findings.open) : item.badge) : 
                             item.badge}
                          </span>
                  }
                      </>
                }
                  </NavLink>;

              return (
                <li key={item.to}>
                    {collapsed ?
                  <Tooltip label={item.label} side="right" className="w-full">
                        {link}
                      </Tooltip> :

                  link
                  }
                  </li>);

            })}
            </ul>
          </div>
        )}
      </div>

      {/* Trust footer + collapse */}
      <div className="border-t border-sidebar-border p-2">
        {!collapsed && showTrust &&
        <div className="mb-2 rounded-md border border-border/80 bg-surface-1/60 px-2.5 py-2">
            <div className="flex items-baseline justify-between">
              <p className="text-[10px] font-semibold uppercase tracking-label text-muted-foreground">
                Trust
              </p>
              <p className="font-mono text-[15px] font-semibold text-primary">
                {currentTrustScore}
              </p>
            </div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-3">
              <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${currentTrustScore}%` }} />
            
            </div>
          </div>
        }
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'flex w-full items-center gap-2.5 rounded-md px-2 py-[7px] text-[13px] font-medium text-muted-foreground transition-colors duration-180 hover:bg-sidebar-accent hover:text-foreground',
            collapsed && 'justify-center px-0'
          )}>
          
          {collapsed ?
          <PanelLeftOpen className="h-[17px] w-[17px]" aria-hidden /> :

          <>
              <PanelLeftClose className="h-[17px] w-[17px]" aria-hidden />
              Collapse
            </>
          }
        </button>
      </div>
    </motion.nav>);

}