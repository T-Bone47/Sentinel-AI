import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Network, Sparkles, X, ArrowRight } from 'lucide-react';
import { GraphCanvas } from '../components/cyber/GraphCanvas';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { MonitoringStatus } from '../components/layout/Header';
import { getOrganizationGraph } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';

export function Graph() {
  const [selected, setSelected] = useState<any | null>(null);
  
  // Fetch the new aggregated graph structure
  const state = useApiResource(
    () => getOrganizationGraph({ aggregated: true }),
    []
  );

  const graphNodes = useMemo(() => state.data?.nodes ?? [], [state.data]);
  const graphEdges = useMemo(() => state.data?.edges ?? [], [state.data]);

  const criticalCount = graphNodes.reduce((acc: number, n: any) => acc + (n.risk_count || 0), 0);

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="relative flex h-full flex-col bg-background">
      {/* Command bar */}
      <div className="glass relative z-10 flex flex-wrap items-center gap-3 border-b border-border px-5 py-3 shadow-md">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-base font-semibold tracking-tight text-foreground">
            <Network className="h-4 w-4 text-primary" aria-hidden />
            Enterprise Relationship Map
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {graphNodes.length} Core Domains · {graphEdges.length} Aggregated Connections · Select a node to trace blast radius
          </p>
        </div>
        <div className="flex-1" />
        <Badge tone="danger" dot>
          {criticalCount} critical items
        </Badge>
        <MonitoringStatus compact />
        <Link to="/copilot">
          <Button variant="ai" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
            Explain this graph
          </Button>
        </Link>
      </div>

      {/* Canvas */}
      <div className="relative min-h-0 flex-1">
        <GraphCanvas
          rawNodes={graphNodes}
          rawEdges={graphEdges}
          selectedId={selected?.id ?? null}
          onSelect={setSelected}
          className="h-full w-full"
        />

        {/* Selection panel */}
        <AnimatePresence>
          {selected && (
            <motion.aside
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              aria-label={`${selected.label} details`}
              className="absolute right-6 top-6 w-[340px] overflow-hidden rounded-xl border border-border bg-surface-1/95 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4 bg-surface-2/50">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-primary">
                    {selected.category}
                  </p>
                  <p className="mt-1 truncate text-lg font-bold text-foreground">{selected.label}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  aria-label="Clear selection"
                  className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="px-5 py-5 space-y-4">
                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Total Records</p>
                    <p className="text-xl font-mono font-medium text-foreground">{selected.count.toLocaleString()}</p>
                  </div>
                  
                  {selected.compliance !== null && selected.compliance !== undefined && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Compliance</p>
                      <p className="text-xl font-mono font-medium text-emerald-400">{selected.compliance}%</p>
                    </div>
                  )}
                </div>

                <div className="rounded-lg border border-border bg-surface-2 p-4">
                  <p className="text-xs text-muted-foreground">{selected.primary_metric}</p>
                  <p className={`mt-1 text-2xl font-mono font-bold ${selected.risk_count > 0 ? 'text-destructive' : 'text-foreground'}`}>
                    {selected.primary_value.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="border-t border-border px-5 py-4 bg-surface-2/30">
                <Button className="w-full justify-between group" variant="primary">
                  Explore {selected.label}
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Button>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}