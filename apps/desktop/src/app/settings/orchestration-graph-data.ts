import type { OrchestrationRecord, RouteGraph } from './orchestration-data'

export const outcomes = ['success', 'failure', 'unavailable', 'uncertain'] as const

export const architectEntries = (graph: RouteGraph) => graph.entry_nodes ?? graph.nodes.map(node => node.id)

export function routeGraph(value: OrchestrationRecord, id: string): RouteGraph {
  if (value.graphs?.[id]) {
    return value.graphs[id]
  }

  const nodes = (value.routes[id] ?? []).map((profile, index) => ({
    id: `step_${index}`,
    label: profile,
    profiles: [profile],
    position: { x: index * 320, y: 80 }
  }))

  return {
    entry: nodes[0]?.id ?? '',
    nodes,
    edges: nodes
      .slice(1)
      .flatMap((node, index) =>
        (['failure', 'unavailable', 'uncertain'] as const).map(on => ({ source: nodes[index].id, target: node.id, on }))
      )
  }
}

export function graphError(graph: RouteGraph, profiles: OrchestrationRecord['profiles'], adaptiveEntry = true): boolean {
  const ids = new Set(graph.nodes.map(node => node.id))

  if (!ids.has(graph.entry) || graph.nodes.length > 64 || ids.size !== graph.nodes.length) {
    return true
  }

  if (
    graph.nodes.some(
      node =>
        !node.profiles.length ||
        node.profiles.length > 32 ||
        node.profiles.some(p => !profiles[p]) ||
        new Set(node.profiles).size !== node.profiles.length
    )
  ) {
    return true
  }

  const ports = new Set(graph.edges.map(e => `${e.source}:${e.on}`))

  if (ports.size !== graph.edges.length || graph.edges.some(e => !ids.has(e.source) || !ids.has(e.target))) {
    return true
  }

  const entries = architectEntries(graph)

  if (!entries.length || entries.some(id => !ids.has(id)) || new Set(entries).size !== entries.length) {return true}
  const reached = new Set(adaptiveEntry ? entries : [graph.entry])

  for (const _node of graph.nodes) {
    for (const edge of graph.edges) {
      if (reached.has(edge.source)) {
        reached.add(edge.target)
      }
    }
  }

  return reached.size !== ids.size
}

export function withGraph(value: OrchestrationRecord, id: string, graph: RouteGraph): OrchestrationRecord {
  return {
    ...value,
    graphs: { ...value.graphs, [id]: graph },
    routes: { ...value.routes, [id]: [...new Set(graph.nodes.flatMap(node => node.profiles))] }
  }
}
