import { Handle, Position } from '@xyflow/react';
import { Shield, ShieldAlert, Activity, Users, Smartphone, Key, Cloud, Box, FileText, CheckSquare, Target, Search, Lock, AlertTriangle, Hexagon } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const ICONS: Record<string, React.ElementType> = {
  Employees: Users,
  IAM: Key,
  Devices: Smartphone,
  Applications: Box,
  'Cloud Assets': Cloud,
  Vendors: Box,
  Policies: FileText,
  Controls: CheckSquare,
  Risks: Target,
  Findings: Search,
  Evidence: Shield,
  Privacy: Lock,
  Consent: Shield,
  Audit: Activity,
};

export function DomainNode({ data, selected }: any) {
  const Icon = ICONS[data.label] || Hexagon;
  const isHighRisk = data.risk_count > 0;
  
  // Blast radius logic sets node opacity via data.opacity
  const isFaded = data.opacity !== undefined && data.opacity < 1;

  return (
    <div 
      className={twMerge(
        clsx(
          "relative min-w-[260px] rounded-xl border p-5 shadow-2xl transition-all duration-500 backdrop-blur-xl bg-black/40",
          selected ? "border-primary/80 shadow-[0_0_30px_-5px_rgba(var(--primary),0.3)] bg-black/60 scale-105 z-10" : "border-white/10 hover:border-primary/50 hover:bg-black/50 hover:shadow-[0_0_20px_-5px_rgba(var(--primary),0.2)] z-0",
          isFaded && "opacity-20 blur-[2px] grayscale-[50%] scale-95",
          isHighRisk && !selected && "border-destructive/30 hover:border-destructive/60 hover:shadow-[0_0_20px_-5px_rgba(var(--destructive),0.2)]",
          isHighRisk && selected && "border-destructive/80 shadow-[0_0_30px_-5px_rgba(var(--destructive),0.3)]",
          "overflow-hidden"
        )
      )}
      data-cursor-hover
    >
      {/* Top accent line */}
      <div className={clsx(
        "absolute top-0 left-0 w-full h-1",
        isHighRisk ? "bg-gradient-to-r from-destructive/80 to-destructive/20" : "bg-gradient-to-r from-primary/80 to-primary/20"
      )} />

      <Handle type="target" position={Position.Left} className={clsx("!w-3 !h-3 !border-2 !border-black", isHighRisk ? "!bg-destructive" : "!bg-primary")} />
      
      {/* Header */}
      <div className="flex items-start gap-4 mb-4">
        <div className={clsx(
          "p-2.5 rounded-lg border shadow-inner backdrop-blur-md",
          isHighRisk ? "bg-destructive/10 border-destructive/30 text-destructive shadow-destructive/10" : "bg-primary/10 border-primary/30 text-primary shadow-primary/10"
        )}>
          <Icon className="w-5 h-5 stroke-[1.5]" />
        </div>
        <div className="pt-1">
          <p className="text-[9px] uppercase font-bold tracking-[0.2em] text-muted-foreground/80 mb-1">{data.category}</p>
          <h3 className="font-mono text-sm font-semibold tracking-wide text-foreground uppercase">
            {data.label}
          </h3>
        </div>
      </div>

      {/* Metrics */}
      <div className="space-y-3 pt-2">
        <div className="flex justify-between items-baseline text-sm">
          <span className="text-xs text-muted-foreground font-medium">Total Entities</span>
          <span className="font-mono text-[15px] font-semibold text-foreground/90">{data.count?.toLocaleString()}</span>
        </div>

        {data.compliance !== null && data.compliance !== undefined && (
          <div className="flex justify-between items-baseline text-sm">
            <span className="text-xs text-muted-foreground font-medium">Compliance</span>
            <span className={clsx(
              "font-mono text-[15px] font-semibold",
              data.compliance < 50 ? "text-destructive" : data.compliance < 80 ? "text-yellow-400" : "text-emerald-400"
            )}>{data.compliance}%</span>
          </div>
        )}

        <div className="h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent my-3" />

        <div className="flex justify-between items-baseline text-sm">
          <span className="text-xs text-muted-foreground font-medium">{data.primary_metric}</span>
          <span className={clsx(
            "font-mono text-[15px] font-semibold flex items-center gap-1.5",
            isHighRisk ? "text-destructive drop-shadow-[0_0_8px_rgba(var(--destructive),0.5)]" : "text-primary drop-shadow-[0_0_8px_rgba(var(--primary),0.3)]"
          )}>
            {isHighRisk && <AlertTriangle className="w-3.5 h-3.5" />}
            {data.primary_value?.toLocaleString() || "0"}
          </span>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className={clsx("!w-3 !h-3 !border-2 !border-black", isHighRisk ? "!bg-destructive" : "!bg-primary")} />
      
      {/* Ambient background glow for high risk */}
      {isHighRisk && (
        <div className="absolute inset-0 bg-destructive/5 blur-xl pointer-events-none -z-10" />
      )}
      
      {/* Radar pulse for selected nodes */}
      {selected && isHighRisk && (
        <div className="absolute inset-0 rounded-xl border border-destructive/40 animate-ping opacity-20 pointer-events-none" />
      )}
      {selected && !isHighRisk && (
        <div className="absolute inset-0 rounded-xl border border-primary/40 animate-ping opacity-20 pointer-events-none" />
      )}
    </div>
  );
}
