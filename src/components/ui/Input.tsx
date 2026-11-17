import { forwardRef, useId } from 'react';
import { AlertCircle, Search } from 'lucide-react';
import { cn } from '../../utils/cn';

const fieldBase =
'w-full rounded-lg border border-input bg-surface-1 text-sm text-foreground placeholder:text-muted-foreground/70 transition-[border-color,box-shadow] duration-180 focus:outline-none focus:border-ring focus:ring-[3px] focus:ring-ring/25 disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-destructive aria-[invalid=true]:ring-[3px] aria-[invalid=true]:ring-destructive/20';

export interface FieldProps {
  label?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  className?: string;
  children: (props: {id: string;describedBy?: string;invalid: boolean;}) => React.ReactNode;
}

export function Field({ label, hint, error, required, className, children }: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = error ? errorId : hint ? hintId : undefined;

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label &&
      <label
        htmlFor={id}
        className="flex items-center gap-1 text-xs font-medium text-foreground">
        
          {label}
          {required &&
        <span className="text-destructive" aria-hidden>
              *
            </span>
        }
        </label>
      }
      {children({ id, describedBy, invalid: Boolean(error) })}
      {error ?
      <p
        id={errorId}
        role="alert"
        className="flex items-center gap-1.5 text-xs text-destructive">
        
          <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {error}
        </p> :
      hint ?
      <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p> :
      null}
    </div>);

}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(fieldBase, 'h-9 px-3', className)} {...props} />;
  }
);

export interface TextareaProps extends
  React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  showCounter?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
{ className, showCounter, maxLength, value, ...props },
ref)
{
  const length = typeof value === 'string' ? value.length : 0;
  return (
    <div className="relative">
      <textarea
        ref={ref}
        value={value}
        maxLength={maxLength}
        className={cn(fieldBase, 'min-h-[96px] resize-y px-3 py-2.5', className)}
        {...props} />
      
      {showCounter && maxLength ?
      <span
        className={cn(
          'pointer-events-none absolute bottom-2 right-3 font-mono text-2xs',
          length > maxLength * 0.9 ? 'text-warning' : 'text-muted-foreground'
        )}>
        
          {length}/{maxLength}
        </span> :
      null}
    </div>);

});

export function SearchInput({
  className,
  wrapperClassName,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {wrapperClassName?: string;}) {
  return (
    <div className={cn('relative', wrapperClassName)}>
      <Search
        aria-hidden
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      
      <input
        type="search"
        className={cn(fieldBase, 'h-9 pl-9 pr-3', className)}
        {...props} />
      
    </div>);

}