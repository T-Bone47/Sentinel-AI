import { useState, useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface DropdownProps {
  trigger: (props: {open: boolean;toggle: () => void;}) => React.ReactNode;
  children: React.ReactNode | ((close: () => void) => React.ReactNode);
  align?: 'start' | 'end';
  className?: string;
  menuClassName?: string;
  label?: string;
}

export function Dropdown({
  trigger,
  children,
  align = 'end',
  className,
  menuClassName,
  label = 'Menu'
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (!wrapper.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div ref={wrapper} className={cn('relative', className)}>
      {trigger({ open, toggle: () => setOpen((v) => !v) })}
      <AnimatePresence>
        {open &&
        <motion.div
          role="menu"
          aria-label={label}
          initial={{ opacity: 0, y: -4, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -4, scale: 0.98 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
          className={cn(
            'absolute z-40 mt-2 min-w-[220px] overflow-hidden rounded-xl border border-border bg-popover p-1.5 shadow-lg',
            align === 'end' ? 'right-0' : 'left-0',
            menuClassName
          )}>
          
            {typeof children === 'function' ? children(close) : children}
          </motion.div>
        }
      </AnimatePresence>
    </div>);

}

export function DropdownItem({
  children,
  icon,
  selected,
  destructive,
  className,
  ...props




}: React.ButtonHTMLAttributes<HTMLButtonElement> & {icon?: React.ReactNode;selected?: boolean;destructive?: boolean;}) {
  return (
    <button
      type="button"
      role="menuitem"
      className={cn(
        'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium transition-colors duration-150',
        destructive ?
        'text-destructive hover:bg-destructive/10' :
        'text-foreground hover:bg-accent',
        className
      )}
      {...props}>
      
      {icon && <span className="text-muted-foreground">{icon}</span>}
      <span className="flex-1 truncate">{children}</span>
      {selected && <Check className="h-3.5 w-3.5 text-primary" aria-hidden />}
    </button>);

}

export function DropdownLabel({ children }: {children: React.ReactNode;}) {
  return (
    <p className="px-2.5 pb-1 pt-2 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </p>);

}

export function DropdownSeparator() {
  return <div className="my-1.5 h-px bg-border" role="separator" />;
}