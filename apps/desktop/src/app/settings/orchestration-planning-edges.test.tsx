import { cleanup, render } from '@testing-library/react'
import type { Edge } from '@xyflow/react'
import { afterEach, expect, it, vi } from 'vitest'

import type { OrchestrationRecord, RouteGraph } from './orchestration-data'
import { GraphCanvas } from './orchestration-graph-canvas'

const capture = vi.hoisted(() => ({ edges: [] as Edge[] }))
vi.mock('@xyflow/react', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  ReactFlow: ({ edges }: { edges: Edge[] }) => { capture.edges = edges;

 return null }
}))
afterEach(cleanup)

it('renders equal architect choices without marking alternatives as uncertain', () => {
  const graph: RouteGraph = {
    entry: 'a', entry_nodes: ['a', 'b', 'c'],
    nodes: ['a', 'b', 'c'].map(id => ({ id, label: id, profiles: ['worker'], position: { x: 0, y: 0 } })),
    edges: [{ source: 'a', target: 'b', on: 'uncertain' }]
  }

  const config: OrchestrationRecord = { profiles: {}, routes: {} }
  const props = { graph, config, profiles: {}, route: 'test', onChange: vi.fn(), onConfigChange: vi.fn(), onAdd: vi.fn(), onSelect: vi.fn() }
  const view = render(<GraphCanvas {...props} />)
  const choices = capture.edges.filter(edge => edge.source === '__planner')
  expect(choices.map(edge => edge.target)).toEqual(['a', 'b', 'c'])
  expect(new Set(choices.map(edge => edge.className))).toEqual(new Set(['planning']))
  expect(capture.edges.find(edge => edge.source === 'a')?.className).toBe('uncertain')
  view.rerender(<GraphCanvas {...props} config={{ ...config, routing: { adaptive_entry: false } }} />)
  expect(capture.edges.filter(edge => edge.source === '__planner').map(edge => edge.target)).toEqual(['a'])
})
