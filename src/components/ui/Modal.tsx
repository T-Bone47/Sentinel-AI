import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Button } from './Button';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  tone?: 'default' | 'ai' | 'danger';
}

const sizes = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl'
};

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  tone = 'default'
}: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, open, onClose);

  return createPortal(
    <AnimatePresence>
      {open &&
      <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
          <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onClose}
          className="absolute inset-0 bg-background/70 backdrop-blur-md"
          aria-hidden />
        
          <motion.div
          ref={ref}
          role="dialog"
          aria-modal="true"
          aria-label={title}
          tabIndex={-1}
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.99 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className={cn(
            'relative w-full overflow-hidden rounded-t-2xl border bg-popover shadow-xl sm:rounded-2xl',
            sizes[size],
            tone === 'ai' ? 'border-ai-border/70 ai-glow' : 'border-border'
          )}>
          
            <header className="flex items-start justify-between gap-6 border-b border-border px-6 py-5">
              <div>
                <h2 className="text-base font-semibold tracking-tight">{title}</h2>
                {description &&
              <p className="mt-1 text-sm text-muted-foreground">{description}</p>
              }
              </div>
              <Button
              variant="ghost"
              size="icon-sm"
              onClick={onClose}
              aria-label="Close dialog">
              
                <X className="h-4 w-4" />
              </Button>
            </header>
            <div className="max-h-[60vh] overflow-y-auto px-6 py-5">{children}</div>
            {footer &&
          <footer className="flex items-center justify-end gap-2 border-t border-border bg-surface-2/60 px-6 py-4">
                {footer}
              </footer>
          }
          </motion.div>
        </div>
      }
    </AnimatePresence>,
    document.body
  );
}