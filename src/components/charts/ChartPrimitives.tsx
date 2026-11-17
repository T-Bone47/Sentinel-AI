import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis } from
'recharts';
import { cn } from '../../utils/cn';
import { resolveToken } from '../../utils/colors';
import { useTheme } from '../../contexts/ThemeContext';

/** Resolves design tokens to concrete colors — SVG attributes cannot use var(). */
function useChartTheme() {
  // Subscribing to the theme forces a re-resolve when the palette flips.
  useTheme();
  const c = (value: string) => resolveToken(value);
  return {
    c,
    axis: {
      stroke: c('var(--muted-foreground)'),
      tickLine: false,
      axisLine: false,
      tick: { fontSize: 11, fill: c('var(--muted-foreground)') }
    },
    grid: c('var(--chart-grid)'),
    cursor: c('var(--border-strong)'),
    fill: resolveToken('var(--accent)')
  };
}

function ChartTooltip({
  active,
  payload,
  label,
  suffix = ''





}: {active?: boolean;payload?: {name?: string;value?: number | string;color?: string;}[];label?: string;suffix?: string;}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-lg">
      {label &&
      <p className="mb-1.5 text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
      }
      <ul className="space-y-1">
        {payload.map((entry, i) =>
        <li key={i} className="flex items-center gap-2 text-xs">
            <span
            className="h-2 w-2 rounded-[3px]"
            style={{ backgroundColor: entry.color }}
            aria-hidden />
          
            <span className="capitalize text-muted-foreground">{entry.name}</span>
            <span className="ml-auto font-mono font-medium text-foreground">
              {entry.value}
              {suffix}
            </span>
          </li>
        )}
      </ul>
    </div>);

}

export function ChartFrame({
  height = 260,
  children,
  className,
  label





}: {height?: number;children: React.ReactElement;className?: string;label: string;}) {
  return (
    <div
      className={cn('w-full', className)}
      style={{ height }}
      role="img"
      aria-label={label}>
      
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>);

}

export function TrendAreaChart({
  data,
  xKey,
  series,
  height = 260,
  label






}: {data: Record<string, string | number>[];xKey: string;series: {key: string;color: string;name: string;}[];height?: number;label: string;}) {
  const t = useChartTheme();
  return (
    <ChartFrame height={height} label={label}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <defs>
          {series.map((s) =>
          <linearGradient key={s.key} id={`fill-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={t.c(s.color)} stopOpacity={0.3} />
              <stop offset="100%" stopColor={t.c(s.color)} stopOpacity={0.02} />
            </linearGradient>
          )}
        </defs>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey={xKey} {...t.axis} />
        <YAxis {...t.axis} width={44} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: t.cursor }} />
        {series.map((s) =>
        <Area
          key={s.key}
          type="monotone"
          dataKey={s.key}
          name={s.name}
          stroke={t.c(s.color)}
          strokeWidth={2}
          fill={`url(#fill-${s.key})`}
          activeDot={{ r: 4, strokeWidth: 0 }}
          animationDuration={700} />

        )}
      </AreaChart>
    </ChartFrame>);

}

export function CompareLineChart({
  data,
  xKey,
  series,
  height = 240,
  label






}: {data: Record<string, string | number>[];xKey: string;series: {key: string;color: string;name: string;dashed?: boolean;}[];height?: number;label: string;}) {
  const t = useChartTheme();
  return (
    <ChartFrame height={height} label={label}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid stroke={t.grid} vertical={false} />
        <XAxis dataKey={xKey} {...t.axis} />
        <YAxis {...t.axis} width={44} domain={[60, 100]} />
        <Tooltip content={<ChartTooltip suffix="%" />} cursor={{ stroke: t.cursor }} />
        {series.map((s) =>
        <Line
          key={s.key}
          type="monotone"
          dataKey={s.key}
          name={s.name}
          stroke={t.c(s.color)}
          strokeWidth={2}
          strokeDasharray={s.dashed ? '4 4' : undefined}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
          animationDuration={700} />

        )}
      </LineChart>
    </ChartFrame>);

}

export function StackedBarsChart({
  data,
  xKey,
  series,
  height = 260,
  layout = 'horizontal',
  label,
  showLegend = false








}: {data: Record<string, string | number>[];xKey: string;series: {key: string;color: string;name: string;}[];height?: number;layout?: 'horizontal' | 'vertical';label: string;showLegend?: boolean;}) {
  const t = useChartTheme();
  const vertical = layout === 'vertical';
  return (
    <ChartFrame height={height} label={label}>
      <BarChart
        data={data}
        layout={layout}
        margin={{ top: 8, right: 12, bottom: 0, left: vertical ? 8 : -18 }}
        barCategoryGap={vertical ? 10 : 16}>
        
        <CartesianGrid stroke={t.grid} vertical={vertical} horizontal={!vertical} />
        {vertical ?
        <>
            <XAxis type="number" {...t.axis} />
            <YAxis type="category" dataKey={xKey} {...t.axis} width={132} />
          </> :

        <>
            <XAxis dataKey={xKey} {...t.axis} />
            <YAxis {...t.axis} width={44} />
          </>
        }
        <Tooltip content={<ChartTooltip />} cursor={{ fill: t.fill, opacity: 0.5 }} />
        {showLegend &&
        <Legend
          iconType="circle"
          iconSize={7}
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />

        }
        {series.map((s, i) =>
        <Bar
          key={s.key}
          dataKey={s.key}
          name={s.name}
          stackId="a"
          fill={t.c(s.color)}
          radius={
          i === series.length - 1 ?
          vertical ?
          [0, 4, 4, 0] :
          [4, 4, 0, 0] :
          undefined
          }
          animationDuration={700} />

        )}
      </BarChart>
    </ChartFrame>);

}

export function DonutChart({
  data,
  height = 200,
  label,
  centerLabel,
  centerValue






}: {data: {name: string;value: number;color: string;}[];height?: number;label: string;centerLabel?: string;centerValue?: string;}) {
  const t = useChartTheme();
  return (
    <div className="relative" style={{ height }}>
      <ChartFrame height={height} label={label}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="66%"
            outerRadius="94%"
            paddingAngle={2}
            stroke="none"
            animationDuration={700}>
            
            {data.map((entry) =>
            <Cell key={entry.name} fill={t.c(entry.color)} />
            )}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
        </PieChart>
      </ChartFrame>
      {(centerValue || centerLabel) &&
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <p className="font-mono text-2xl font-semibold tracking-tight">{centerValue}</p>
          <p className="text-2xs uppercase tracking-wider text-muted-foreground">
            {centerLabel}
          </p>
        </div>
      }
    </div>);

}

/** Lightweight inline sparkline — no chart library overhead. */
export function Sparkline({
  values,
  color = 'var(--primary)',
  width = 88,
  height = 28





}: {values: number[];color?: string;width?: number;height?: number;}) {
  useTheme();
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values.
  map((v, i) => {
    const x = i / (values.length - 1) * width;
    const y = height - (v - min) / span * (height - 4) - 2;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).
  join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <polyline
        points={points}
        fill="none"
        stroke={resolveToken(color)}
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke" />
      
    </svg>);

}