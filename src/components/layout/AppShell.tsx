import { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { CommandPalette } from './CommandPalette';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { LiquidCursor } from '../ui/LiquidCursor';

/** Routes that own the full canvas (no page padding / max width). */
const FULL_BLEED = ['/graph'];

export function AppShell() {
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const fullBleed = FULL_BLEED.includes(pathname);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <LiquidCursor />
      
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[70] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-primary-foreground">
        
        Skip to content
      </a>

      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((v) => !v)}
        className="hidden lg:flex" />
      

      {/* Mobile navigation */}
      <AnimatePresence>
        {mobileNav &&
        <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileNav(false)}
            className="absolute inset-0 bg-background/75 backdrop-blur-md"
            aria-hidden />
          
            <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-y-0 left-0">
            
              <Sidebar
              collapsed={false}
              onToggle={() => setMobileNav(false)}
              onNavigate={() => setMobileNav(false)}
              className="shadow-xl" />
            
            </motion.div>
          </div>
        }
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          onOpenCommand={() => setCommandOpen(true)}
          onOpenMobileNav={() => setMobileNav(true)} />
        
        <main id="main" className="relative flex-1 overflow-y-auto">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              fullBleed ?
              'h-full' :
              'mx-auto w-full max-w-[1560px] px-4 py-5 sm:px-5 lg:px-6 lg:py-6'
            )}>
            
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </motion.div>
        </main>
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>);

}