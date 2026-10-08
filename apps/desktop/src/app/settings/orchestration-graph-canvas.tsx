import '@xyflow/react/dist/style.css'
import './orchestration-graph.css'

import {
  Background,
  Controls,
  type Edge,
  Handle,
  MiniMap,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState
} from '@xyflow/react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { useI18n } from '@/i18n'
import { graphCopy } from '@/i18n/orchestration-graph'

import type { OrchestrationRecord, RouteGraph, RouteNode } from './orchestration-data'
import { architectEntries, outcomes } from './orchestration-graph-data'
import { PLANNER_NODE, Planning, type PlanningNode, reviewLabel } from './orchestration-role-nodes'
import { MeasuredViewport } from './orchestration-viewport'

interface PoolData extends Record<string, unknown> {
  node: RouteNode
  entry: boolean
  review: string
  profiles: OrchestrationRecord['profiles']
}
type PoolNode = Node<PoolData, 'pool'>
type WorkflowNode = PoolNode | PlanningNode

function ModelPool({ data, selected }: NodeProps<PoolNode>) {
  const { locale } = useI18n()
  const c = graphCopy(locale)

  return (
    <div className={`orchestration-pool${selected ? ' selected' : ''}`}>
      <Handle id="input" position={Position.Left} type="target" />
      <div className="orchestration-pool-title">
        {data.entry && <span>▶ </span>}
        {data.node.label || c.group}
      </div>
      <div className="orchestration-pool-models">
        {data.node.profiles.map((id, index) => (
          <div key={id} title={data.profiles[id]?.description}>
            {index + 1}. {data.profiles[id]?.model || id}
            {data.profiles[id]?.enabled ? '' : ' ○'}
          </div>
        ))}
        <p className="text-muted-foreground">{data.review}</p>
        {data.node.description && <p className="text-muted-foreground">{data.node.description}</p>}
      </div>
      {outcomes.map(outcome => (
        <div className={`orchestration-port ${outcome}`} key={outcome}>
          {c.outcomes[outcome]}
          <Handle id={outcome} position={Position.Right} type="source" />
        </div>
      ))}
    </div>
  )
}

const nodeTypes = { pool: ModelPool, planning: Planning }

interface Props {
  config: OrchestrationRecord
  route: string
  onConfigChange: (value: OrchestrationRecord) => void
  graph: RouteGraph
  profiles: OrchestrationRecord['profiles']
  onChange: (graph: RouteGraph) => void
  onSelect: (id: string) => void
  onAdd: (position: { x: number; y: number }) => void
}

export function GraphCanvas({ graph, profiles, onChange, onSelect, onAdd, config, route, onConfigChange }: Props) {
  const { locale } = useI18n()
  const container = useRef<HTMLDivElement>(null)

  const initial = useMemo<WorkflowNode[]>(
    () => [
      {
        id: PLANNER_NODE,
        type: 'planning',
        position: {
          x: Math.min(0, ...graph.nodes.map(n => n.position.x)) - 320,
          y: graph.nodes.find(n => n.id === graph.entry)?.position.y ?? 80
        },
        deletable: false,
        draggable: false,
        selectable: false,
        connectable: config.routing?.adaptive_entry !== false,
        data: { config, route, onChange: onConfigChange }
      },
      ...graph.nodes.map(node => ({
        id: node.id,
        type: 'pool' as const,
        position: node.position,
        data: { node, entry: node.id === graph.entry && config.routing?.adaptive_entry === false, profiles, review: reviewLabel(config, locale) }
      }))
    ],
    [graph, profiles, config, route, onConfigChange, locale]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initial)
  const [flow, setFlow] = useState<ReactFlowInstance<WorkflowNode> | null>(null)
  useEffect(() => setNodes(current => initial.map(node => ({ ...current.find(item => item.id === node.id), ...node }))), [initial, setNodes])

  const initialEdges = useMemo<Edge[]>(
    () => [
      ...graph.nodes
        .filter(n => config.routing?.adaptive_entry !== false ? architectEntries(graph).includes(n.id) : n.id === graph.entry)
        .map(n => ({
          id: `__plan:${n.id}`,
          source: PLANNER_NODE,
          target: n.id,
          sourceHandle: 'plan',
          targetHandle: 'input',
          deletable: config.routing?.adaptive_entry !== false,
          selectable: config.routing?.adaptive_entry !== false,
          className: 'planning'
        })),
      ...graph.edges.map(edge => ({
        id: `${edge.source}:${edge.on}`,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.on,
        targetHandle: 'input',
        className: edge.on,
        type: 'default'
      }))
    ],
    [graph, config.routing?.adaptive_entry]
  )

  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initialEdges)
  useEffect(() => setEdges(initialEdges), [initialEdges, setEdges])

  return (
    <div
      className="orchestration-canvas"
      onContextMenu={event => { event.preventDefault(); event.stopPropagation() }}
      onDoubleClick={event => {
        if ((event.target as HTMLElement).classList.contains('react-flow__pane') && flow) {
          onAdd(flow.screenToFlowPosition({ x: event.clientX, y: event.clientY }))
        }
      }}
      ref={container}
    >
      <ReactFlow
        deleteKeyCode={['Backspace', 'Delete']}
        edges={edges}
        isValidConnection={connection =>
          (connection.source !== PLANNER_NODE || config.routing?.adaptive_entry !== false) &&
          connection.target !== PLANNER_NODE &&
          connection.source !== connection.target &&
          connection.targetHandle === 'input'
        }
        maxZoom={2}
        minZoom={0.2}
        nodes={nodes}
        nodeTypes={nodeTypes}
        onConnect={connection => {
          if (connection.source === PLANNER_NODE) {
            onChange({ ...graph, entry_nodes: [...new Set([...architectEntries(graph), connection.target])] })

            return
          }

          const on = outcomes.find(outcome => outcome === connection.sourceHandle)

          if (on) {
            onChange({
              ...graph,
              edges: [
                ...graph.edges.filter(e => e.source !== connection.source || e.on !== on),
                { source: connection.source, target: connection.target, on }
              ]
            })
          }
        }}
        onDelete={({ nodes: deleted, edges: deletedEdges }) =>
          onChange({
            ...graph,
            nodes: graph.nodes.filter(n => !deleted.some(d => d.id === n.id)),
            entry: deleted.some(d => d.id === graph.entry) ? graph.nodes.find(n => !deleted.some(d => d.id === n.id))?.id ?? '' : graph.entry,
            entry_nodes: architectEntries(graph).filter(id => !deleted.some(d => d.id === id) && !deletedEdges.some(e => e.id === `__plan:${id}`)),
            edges: graph.edges.filter(
              e =>
                !deleted.some(d => d.id === e.source || d.id === e.target) &&
                !deletedEdges.some(d => d.id === `${e.source}:${e.on}`)
            )
          })
        }
        onEdgesChange={onEdgesChange}
        onInit={setFlow}
        onNodeClick={(_event, node) => onSelect(node.id)}
        onNodeDragStop={(_event, node) =>
          onChange({
            ...graph,
            nodes: graph.nodes.map(n => (n.id === node.id ? { ...n, position: node.position } : n))
          })
        }
        onNodesChange={onNodesChange}
        zoomOnDoubleClick={false}
      >
        <MeasuredViewport container={container} count={graph.nodes.length} />
        <Background gap={20} />
        <Controls />
        <MiniMap pannable style={{ width: 120, height: 80 }} zoomable />
      </ReactFlow>
    </div>
  )
}
