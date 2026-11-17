import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export type ButtonVariant =
'primary' |
'secondary' |
'ghost' |
'outline' |
'danger' |
'ai' |
'link';

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'icon-sm' | 'icon' | 'icon-lg';

const base =
'relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-[background-color,color,box-shadow,transform,border-color] duration-180 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50';

const variants: Record<ButtonVariant, string> = {
  primary:
  'bg-primary text-primary-foreground shadow-xs hover:bg-primary-hover hover:shadow-sm',
  secondary:
  'bg-secondary text-secondary-foreground border border-border hover:bg-accent hover:border-border-strong',
  ghost: 'text-muted-foreground hover:bg-accent hover:text-foreground',
  outline:
  'border border-border bg-transparent text-foreground hover:bg-accent hover:border-border-strong',
  danger:
  'bg-destructive text-destructive-foreground shadow-xs hover:brightness-110 focus-visible:ring-destructive/60',
  ai: 'ai-gradient text-white shadow-sm hover:brightness-110 focus-visible:ring-ai/70',
  link: 'text-primary underline-offset-4 hover:underline px-0'
};

const sizes: Record<ButtonSize, string> = {
  xs: 'h-7 px-2.5 text-xs',
  sm: 'h-8 px-3 text-[13px]',
  md: 'h-9 px-3.5 text-sm',
  lg: 'h-10 px-5 text-sm',
  'icon-sm': 'h-7 w-7',
  icon: 'h-9 w-9',
  'icon-lg': 'h-10 w-10'
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
{
  className,
  variant = 'secondary',
  size = 'md',
  loading = false,
  iconLeft,
  iconRight,
  children,
  disabled,
  type = 'button',
  ...props
},
ref)
{
  return (
    <button
      ref={ref}
      type={type}
      data-variant={variant}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}>
      
      {loading ?
      <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> :

      iconLeft
      }
      {children}
      {!loading && iconRight}
    </button>);

});

/** Split button: primary action + attached menu trigger. */
export function SplitButton({
  children,
  onAction,
  menuTrigger,
  variant = 'primary',
  size = 'md',
  className







}: {children: React.ReactNode;onAction?: () => void;menuTrigger: React.ReactNode;variant?: ButtonVariant;size?: ButtonSize;className?: string;}) {
  return (
    <div className={cn('inline-flex items-stretch', className)}>
      <Button
        variant={variant}
        size={size}
        onClick={onAction}
        className="rounded-r-none">
        
        {children}
      </Button>
      <div className="w-px bg-black/15 dark:bg-black/30" aria-hidden />
      {menuTrigger}
    </div>);

}