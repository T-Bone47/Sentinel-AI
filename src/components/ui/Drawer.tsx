import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Button } from './Button';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  eyebrow?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: 'md' | 'lg' | 'xl';
}

const widths = {
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-2xl'
};

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  eyebrow,
  children,
  footer,
  width = 'lg'
}: DrawerProps) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, open, onClose);

  return createPortal(
    <AnimatePresence>
      {open &&
      <div className="fixed inset-0 z-50">
          <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onClose}
          className="absolute inset-0 bg-background/70 backdrop-blur-md"
          aria-hidden />
        
          <motion.aside
          ref={ref}
          role="dialog"
          aria-modal="true"
          aria-label={title}
          tabIndex={-1}
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          className={cn(
            'absolute inset-y-0 right-0 flex w-full flex-col border-l border-border bg-popover shadow-xl',
            widths[width]
          )}>
          
            <header className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div className="min-w-0">
                {eyebrow && <div className="mb-2">{eyebrow}</div>}
                <h2 className="truncate text-base font-semibold tracking-tight">
                  {title}
                </h2>
                {subtitle &&
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
              }
              </div>
              <Button
              variant="ghost"
              size="icon-sm"
              onClick={onClose}
              aria-label="Close panel">
              
                <X className="h-4 w-4" />
              </Button>
            </header>
            <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
            {footer &&
          <footer className="flex items-center justify-end gap-2 border-t border-border bg-surface-2/60 px-6 py-4">
                {footer}
              </footer>
          }
          </motion.aside>
        </div>
      }
    </AnimatePresence>,
    document.body
  );
}