import { useId } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
}

export function Tabs({
  items,
  value,
  onChange,
  className,
  ariaLabel = 'Sections'






}: {items: TabItem[];value: string;onChange: (id: string) => void;className?: string;ariaLabel?: string;}) {
  const groupId = useId();

  const onKeyDown = (event: React.KeyboardEvent) => {
    const index = items.findIndex((i) => i.id === value);
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      onChange(items[(index + 1) % items.length].id);
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      onChange(items[(index - 1 + items.length) % items.length].id);
    }
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      onKeyDown={onKeyDown}
      className={cn(
        'scrollbar-none flex items-center gap-1 overflow-x-auto border-b border-border',
        className
      )}>
      
      {items.map((item) => {
        const active = item.id === value;
        return (
          <button
            key={item.id}
            role="tab"
            type="button"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(item.id)}
            className={cn(
              'relative flex items-center gap-2 whitespace-nowrap px-3 py-2.5 text-[13px] font-medium transition-colors duration-180',
              active ?
              'text-foreground' :
              'text-muted-foreground hover:text-foreground'
            )}>
            
            {item.icon}
            {item.label}
            {typeof item.count === 'number' &&
            <span
              className={cn(
                'rounded-md px-1.5 py-0.5 font-mono text-2xs',
                active ? 'bg-primary/12 text-primary' : 'bg-muted text-muted-foreground'
              )}>
              
                {item.count}
              </span>
            }
            {active &&
            <motion.span
              layoutId={`tab-underline-${groupId}`}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-x-1 -bottom-px h-0.5 rounded-full bg-primary" />

            }
          </button>);

      })}
    </div>);

}

export function SegmentedControl({
  items,
  value,
  onChange,
  className,
  ariaLabel = 'View'






}: {items: {id: string;label: string;icon?: React.ReactNode;}[];value: string;onChange: (id: string) => void;className?: string;ariaLabel?: string;}) {
  const groupId = useId();
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface-2 p-0.5',
        className
      )}>
      
      {items.map((item) => {
        const active = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(item.id)}
            className={cn(
              'relative flex items-center gap-1.5 rounded-[7px] px-2.5 py-1.5 text-xs font-medium transition-colors duration-180',
              active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
            )}>
            
            {active &&
            <motion.span
              layoutId={`segment-${groupId}`}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 rounded-[7px] bg-surface-1 shadow-xs" />

            }
            <span className="relative flex items-center gap-1.5">
              {item.icon}
              {item.label}
            </span>
          </button>);

      })}
    </div>);

}