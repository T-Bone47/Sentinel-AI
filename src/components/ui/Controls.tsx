import { forwardRef } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: {value: string;label: string;}[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
{ className, options, ...props },
ref)
{
  return (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          'h-9 w-full appearance-none rounded-lg border border-input bg-surface-1 pl-3 pr-8 text-sm text-foreground transition-[border-color,box-shadow] duration-180 focus:border-ring focus:outline-none focus:ring-[3px] focus:ring-ring/25 disabled:opacity-60',
          className
        )}
        {...props}>
        
        {options.map((o) =>
        <option key={o.value} value={o.value}>
            {o.label}
          </option>
        )}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      
    </div>);

});

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
  id







}: {checked: boolean;onChange: (value: boolean) => void;label?: string;description?: string;disabled?: boolean;id?: string;}) {
  const control =
  <button
    id={id}
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={cn(
      'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors duration-180 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50',
      checked ? 'border-primary bg-primary' : 'border-border bg-muted'
    )}>
    
      <span
      className={cn(
        'inline-block h-3.5 w-3.5 rounded-full bg-surface-1 shadow-xs transition-transform duration-180',
        checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
      )} />
    
    </button>;


  if (!label) return control;

  return (
    <div className="flex items-start justify-between gap-6">
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description &&
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            {description}
          </p>
        }
      </div>
      {control}
    </div>);

}

export function Checkbox({
  checked,
  indeterminate,
  onChange,
  label,
  className






}: {checked: boolean;indeterminate?: boolean;onChange: (value: boolean) => void;label: string;className?: string;}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={indeterminate ? 'mixed' : checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        checked || indeterminate ?
        'border-primary bg-primary text-primary-foreground' :
        'border-border-strong bg-surface-1 hover:border-primary/60',
        className
      )}>
      
      {indeterminate ?
      <span className="h-0.5 w-2 rounded-full bg-current" aria-hidden /> :
      checked ?
      <Check className="h-3 w-3" strokeWidth={3} aria-hidden /> :
      null}
    </button>);

}

export function Kbd({ children }: {children: React.ReactNode;}) {
  return (
    <kbd className="inline-flex h-5 min-w-[20px] items-center justify-center rounded border border-border bg-surface-2 px-1.5 font-mono text-2xs text-muted-foreground">
      {children}
    </kbd>);

}