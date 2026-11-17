import { useEffect, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  BackgroundVariant,
  Edge,
  Node,
  MarkerType,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { DomainNode } from './DomainNode';
import { cn } from '../../utils/cn';

// Register the custom node
const nodeTypes = {
  domain: DomainNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

/**
 * Layout nodes using Dagre for a clean hierarchical top-to-bottom or left-to-right map
 */
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 200 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 280, height: 160 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = direction === 'LR' ? Position.Left : Position.Top;
    node.sourcePosition = direction === 'LR' ? Position.Right : Position.Bottom;

    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - 280 / 2,
      y: nodeWithPosition.y - 160 / 2,
    };
  });

  return { nodes, edges };
};

export function GraphCanvas({
  rawNodes,
  rawEdges,
  selectedId,
  onSelect,
  className,
}: {
  rawNodes: any[];
  rawEdges: any[];
  selectedId?: string | null;
  onSelect?: (node: any | null) => void;
  className?: string;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Compute blast radius
  const connectedNodes = useMemo(() => {
    if (!selectedId) return null;
    const connected = new Set([selectedId]);
    rawEdges.forEach((e) => {
      if (e.source === selectedId) connected.add(e.target);
      if (e.target === selectedId) connected.add(e.source);
    });
    return connected;
  }, [selectedId, rawEdges]);

  useEffect(() => {
    if (!rawNodes || !rawNodes.length) return;

    const initialNodes: Node[] = rawNodes.map((n) => ({
      id: n.id,
      type: 'domain',
      position: { x: 0, y: 0 }, // Dagre will set this
      data: {
        ...n,
        opacity: connectedNodes ? (connectedNodes.has(n.id) ? 1 : 0.2) : 1,
      },
    }));

    const initialEdges: Edge[] = rawEdges.map((e) => {
      const isConnected = connectedNodes 
        ? connectedNodes.has(e.source) && connectedNodes.has(e.target)
        : false;

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        animated: isConnected,
        style: {
          stroke: isConnected ? 'oklch(var(--primary))' : 'oklch(var(--muted-foreground))',
          strokeWidth: isConnected ? 2 : 1,
          opacity: connectedNodes ? (isConnected ? 1 : 0.1) : 0.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isConnected ? 'oklch(var(--primary))' : 'oklch(var(--muted-foreground))',
        },
      };
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      initialNodes,
      initialEdges,
      'LR' // Left to right hierarchical
    );

    // Ensure selected state is passed to nodes
    const styledNodes = layoutedNodes.map(n => ({
      ...n,
      selected: n.id === selectedId
    }));

    setNodes(styledNodes);
    setEdges(layoutedEdges);
  }, [rawNodes, rawEdges, selectedId, connectedNodes]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    // Re-construct original raw node format for the parent handler
    if (onSelect) {
      onSelect(rawNodes.find(n => n.id === node.id) || null);
    }
  }, [onSelect, rawNodes]);

  const onPaneClick = useCallback(() => {
    if (onSelect) onSelect(null);
  }, [onSelect]);

  return (
    <div className={cn('relative w-full h-full bg-background', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        className="cyber-grid"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={2} color="oklch(var(--muted-foreground) / 0.2)" />
        <Controls className="!bg-surface-2 !border-surface-3 !text-foreground [&>button]:!border-surface-3 [&>button:hover]:!bg-surface-3" />
      </ReactFlow>
    </div>
  );
}