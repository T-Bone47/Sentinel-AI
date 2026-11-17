import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export function Tooltip({
  label,
  children,
  side = 'top',
  className





}: {label: React.ReactNode;children: React.ReactNode;side?: 'top' | 'right' | 'bottom';className?: string;}) {
  const [open, setOpen] = useState(false);

  const position = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2'
  }[side];

  return (
    <span
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}>
      
      {children}
      <AnimatePresence>
        {open &&
        <motion.span
          role="tooltip"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.15 }}
          className={cn(
            'pointer-events-none absolute z-50 whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-2xs font-medium text-popover-foreground shadow-md',
            position
          )}>
          
            {label}
          </motion.span>
        }
      </AnimatePresence>
    </span>);

}