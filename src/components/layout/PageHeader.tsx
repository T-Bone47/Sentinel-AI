import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  meta,
  className







}: {eyebrow?: React.ReactNode;title: string;subtitle: string;actions?: React.ReactNode;meta?: React.ReactNode;className?: string;}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        'flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between',
        className
      )}>
      
      <div className="min-w-0">
        {eyebrow && <div className="mb-2.5 flex items-center gap-2">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[28px]">
          {title}
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          {subtitle}
        </p>
        {meta &&
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">{meta}</div>
        }
      </div>
      {actions &&
      <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      }
    </motion.header>);

}

export function MetaStat({
  label,
  value,
  icon




}: {label: string;value: string;icon?: React.ReactNode;}) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      {icon}
      {label}
      <span className="font-medium text-foreground">{value}</span>
    </span>);

}