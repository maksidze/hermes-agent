import { expect, it } from 'vitest'

import { type OrchestrationRecord, validOrchestration } from './orchestration-data'
import { routeGraph, withGraph } from './orchestration-graph-data'

const value: OrchestrationRecord = {
  profiles: {
    small: { enabled: true, provider: 'local', model: 'a', level: 'fast' },
    large: { enabled: true, provider: 'local', model: 'b', level: 'deep' }
  },
  routes: { general: ['small', 'large'] }
}

it('migrates routes with success stopping and other outcomes preserving the next choice', () => {
  const graph = routeGraph(value, 'general')
  expect(graph.entry).toBe('step_0')
  expect(graph.edges.map(edge => edge.on)).toEqual(['failure', 'unavailable', 'uncertain'])
  expect(validOrchestration(withGraph(value, 'general', graph))).toBe(true)
})
it('allows explicit downward connections and multiple models, but blocks dangling groups', () => {
  const graph = routeGraph(value, 'general')
  graph.nodes[0].profiles = ['large', 'small']
  graph.entry = 'step_1'
  graph.edges = [{ source: 'step_1', target: 'step_0', on: 'failure' }]
  expect(validOrchestration(withGraph(value, 'general', graph))).toBe(true)
  graph.edges = []
  expect(validOrchestration(withGraph({ ...value, routing: { adaptive_entry: false } }, 'general', graph))).toBe(false)
})

it('allows independent architect choices, but still rejects invalid connections', () => {
  const graph = routeGraph(value, 'general')
  graph.edges = []
  graph.entry_nodes = graph.nodes.map(n => n.id)
  expect(validOrchestration(withGraph(value, 'general', graph))).toBe(true)
  graph.entry_nodes = [graph.entry]
  expect(validOrchestration(withGraph(value, 'general', graph))).toBe(false)
  graph.edges = [{ source: 'step_0', target: 'missing', on: 'failure' }]
  expect(validOrchestration(withGraph(value, 'general', graph))).toBe(false)
})
