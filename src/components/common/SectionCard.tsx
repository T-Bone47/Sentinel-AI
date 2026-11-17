import { cn } from '../../utils/cn';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card';

/** Standard titled panel used across dashboards for consistent rhythm. */
export function SectionCard({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
  tone = 'default',
  delay = 0









}: {title: string;description?: string;actions?: React.ReactNode;children: React.ReactNode;className?: string;bodyClassName?: string;tone?: 'default' | 'ai';delay?: number;}) {
  return (
    <Card
      tone={tone}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: [0.22, 1, 0.36, 1] }}
      className={cn('flex flex-col', className)}>
      
      <CardHeader>
        <div className="min-w-0">
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </CardHeader>
      <CardContent className={cn('flex-1', bodyClassName)}>{children}</CardContent>
    </Card>);

}