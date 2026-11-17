import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '../../utils/cn';

type Tone = 'default' | 'ai' | 'flush';

export interface CardProps extends HTMLMotionProps<'section'> {
  tone?: Tone;
  interactive?: boolean;
}

const tones: Record<Tone, string> = {
  default: 'bg-card/80 backdrop-blur-xl border-border',
  ai: 'bg-ai-surface/40 backdrop-blur-xl border-ai-border/60',
  flush: 'bg-surface-1/80 backdrop-blur-xl border-transparent'
};

export function Card({
  className,
  tone = 'default',
  interactive = false,
  children,
  ...props
}: CardProps) {
  return (
    <motion.section
      className={cn(
        'relative rounded-xl border shadow-xs transition-[box-shadow,border-color,transform] duration-220',
        tones[tone],
        interactive &&
        'cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70',
        className
      )}
      {...props}>
      
      {children}
    </motion.section>);

}

export function CardHeader({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 px-5 pt-5 pb-4',
        className
      )}
      {...props}>
      
      {children}
    </div>);

}

export function CardTitle({
  className,
  children,
  as: As = 'h2',
  ...props
}: React.HTMLAttributes<HTMLHeadingElement> & {as?: 'h2' | 'h3' | 'h4';}) {
  return (
    <As
      className={cn('text-sm font-semibold tracking-tight text-foreground', className)}
      {...props}>
      
      {children}
    </As>);

}

export function CardDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('mt-1 text-xs text-muted-foreground', className)} {...props}>
      {children}
    </p>);

}

export function CardContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-5 pb-5', className)} {...props}>
      {children}
    </div>);

}

export function CardFooter({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 border-t border-border px-5 py-3',
        className
      )}
      {...props}>
      
      {children}
    </div>);

}