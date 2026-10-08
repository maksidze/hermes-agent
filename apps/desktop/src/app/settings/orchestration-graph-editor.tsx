import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/i18n'
import { graphCopy } from '@/i18n/orchestration-graph'

import { nextId, type OrchestrationRecord, type RouteGraph, type RouteNode } from './orchestration-data'
import { Choice } from './orchestration-editors'
import { GraphCanvas } from './orchestration-graph-canvas'
import { architectEntries, graphError, routeGraph, withGraph } from './orchestration-graph-data'
import { ReviewSettings } from './orchestration-role-nodes'
import { ListRow } from './primitives'

interface Props {
  value: OrchestrationRecord
  onChange: (value: OrchestrationRecord) => void
}

export function RouteEditor({ value, onChange }: Props) {
  const { locale } = useI18n()
  const c = graphCopy(locale)
  const [selected, setSelected] = useState(Object.keys(value.routes)[0] ?? '')
  const id = value.routes[selected] ? selected : Object.keys(value.routes)[0]

  const remove = () => {
    const routes = { ...value.routes },
      graphs = { ...value.graphs }

    delete routes[id]
    delete graphs[id]
    onChange({ ...value, routes, graphs })
  }

  const rename = (name: string) => {
    if (name === id || !/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(name) || value.routes[name]) {
      return
    }

    const routes = { ...value.routes, [name]: value.routes[id] },
      graphs = { ...value.graphs }

    delete routes[id]

    if (graphs[id]) {
      graphs[name] = graphs[id]
      delete graphs[id]
    }

    onChange({
      ...value,
      routes,
      graphs,
      routing: {
        ...value.routing,
        default_route: value.routing?.default_route === id ? name : value.routing?.default_route
      },
      specializations: Object.fromEntries(
        Object.entries(value.specializations ?? {}).map(([key, category]) => [
          key,
          { ...category, route: category.route === id ? name : category.route }
        ])
      )
    })
    setSelected(name)
  }

  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">{c.help}</p>
      {id && (
        <ListRow
          action={
            <Input
              aria-label={`${id} id`}
              defaultValue={id}
              key={id}
              onBlur={event => rename(event.target.value.trim())}
            />
          }
          title={c.route}
        />
      )}
      <div className="flex flex-wrap gap-2">
        <Choice label={c.route} onChange={setSelected} options={Object.keys(value.routes)} value={id ?? ''} />
        <Button
          onClick={() => {
            const name = Object.keys(value.routes).length ? nextId(value.routes, 'route') : 'general'
            onChange({ ...value, routes: { ...value.routes, [name]: [] } })
            setSelected(name)
          }}
          variant="outline"
        >
          {c.addRoute}
        </Button>
        <Button
          disabled={
            !id ||
            value.routing?.default_route === id ||
            Object.values(value.specializations ?? {}).some(category => category.route === id)
          }
          onClick={remove}
          variant="ghost"
        >
          {c.remove}
        </Button>
      </div>
      {id && (
        <WorkflowEditor
          config={value}
          graph={routeGraph(value, id)}
          key={id}
          onChange={graph => onChange(withGraph(value, id, graph))}
          onConfigChange={onChange}
          profiles={value.profiles}
          route={id}
        />
      )}
    </div>
  )
}

interface WorkflowProps {
  config: OrchestrationRecord
  route: string
  onConfigChange: (value: OrchestrationRecord) => void
  graph: RouteGraph
  profiles: OrchestrationRecord['profiles']
  onChange: (graph: RouteGraph) => void
}

function WorkflowEditor({ graph, profiles, onChange, config, route, onConfigChange }: WorkflowProps) {
  const { locale } = useI18n()
  const c = graphCopy(locale)
  const [selected, setSelected] = useState(graph.entry)
  const [history, setHistory] = useState<RouteGraph[]>([])
  const [future, setFuture] = useState<RouteGraph[]>([])
  const [newProfile, setNewProfile] = useState(Object.keys(profiles)[0] ?? '')

  const change = (next: RouteGraph) => {
    setHistory(previous => [...previous.slice(-39), graph])
    setFuture([])
    onChange(next)
  }

  const add = (position = { x: graph.nodes.length * 300, y: 80 }) => {
    const id = nextId(Object.fromEntries(graph.nodes.map(n => [n.id, n])), 'group')
    const profile = newProfile
    change({
      ...graph,
      entry: graph.entry || id,
      entry_nodes: graph.nodes.length ? architectEntries(graph) : [id],
      nodes: [...graph.nodes, { id, label: profiles[profile]?.model || c.group, profiles: profile ? [profile] : [], position }]
    })
    setSelected(id)
  }

  const node = graph.nodes.find(n => n.id === selected)

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        <Choice label={c.addModel} labels={Object.fromEntries(Object.entries(profiles).map(([id, p]) => [id, p.model || id]))} onChange={setNewProfile} options={Object.keys(profiles)} value={newProfile} />
        <Button disabled={!profiles[newProfile] || graph.nodes.length >= 64} onClick={() => add()} variant="outline">
          {c.add}
        </Button>
        <Button
          disabled={!history.length}
          onClick={() => {
            setFuture(next => [graph, ...next])
            onChange(history[history.length - 1])
            setHistory(previous => previous.slice(0, -1))
          }}
          variant="ghost"
        >
          {c.undo}
        </Button>
        <Button
          disabled={!future.length}
          onClick={() => {
            setHistory(previous => [...previous, graph])
            onChange(future[0])
            setFuture(next => next.slice(1))
          }}
          variant="ghost"
        >
          {c.redo}
        </Button>
      </div>
      <GraphCanvas
        config={config}
        graph={graph}
        onAdd={add}
        onChange={change}
        onConfigChange={onConfigChange}
        onSelect={setSelected}
        profiles={profiles}
        route={route}
      />
      <ReviewSettings onChange={onConfigChange} value={config} />
      <p className="text-xs text-muted-foreground">{c.endings}</p>
      {graphError(graph, profiles, config.routing?.adaptive_entry !== false) && (
        <p className="text-sm text-destructive" role="alert">
          {c.invalid}
        </p>
      )}
      {node ? (
        <NodeInspector
          entry={graph.entry === node.id}
          node={node}
          onChange={next => change({ ...graph, nodes: graph.nodes.map(n => (n.id === node.id ? next : n)) })}
          onDelete={() =>
            change({
              ...graph,
              nodes: graph.nodes.filter(n => n.id !== node.id),
              entry: graph.entry === node.id ? graph.nodes.find(n => n.id !== node.id)?.id ?? '' : graph.entry,
              entry_nodes: architectEntries(graph).filter(id => id !== node.id),
              edges: graph.edges.filter(e => e.source !== node.id && e.target !== node.id)
            })
          }
          onEntry={() => change({ ...graph, entry: node.id })}
          profiles={profiles}
        />
      ) : (
        <p className="text-sm text-muted-foreground">{c.select}</p>
      )}
    </div>
  )
}

interface InspectorProps {
  node: RouteNode
  profiles: OrchestrationRecord['profiles']
  entry: boolean
  onEntry: () => void
  onDelete: () => void
  onChange: (node: RouteNode) => void
}

function NodeInspector({ node, profiles, entry, onEntry, onDelete, onChange }: InspectorProps) {
  const { locale } = useI18n()
  const c = graphCopy(locale)
  const labels = Object.fromEntries(Object.entries(profiles).map(([id, p]) => [id, `${p.model || id} · ${id}`]))
  const available = Object.keys(profiles).filter(id => !node.profiles.includes(id))

  return (
    <div className="grid gap-2">
      <ListRow
        action={
          <Input
            aria-label={c.name}
            maxLength={100}
            onChange={event => onChange({ ...node, label: event.target.value })}
            value={node.label}
          />
        }
        title={c.name}
      />
      <ListRow
        action={
          <Input
            aria-label={c.description}
            maxLength={1000}
            onChange={event => onChange({ ...node, description: event.target.value })}
            value={node.description ?? ''}
          />
        }
        title={c.description}
      />
      <div className="flex gap-2">
        <Button disabled={entry} onClick={onEntry} variant="outline">
          {c.entry}
        </Button>
        <Button onClick={onDelete} variant="ghost">
          {c.remove}
        </Button>
      </div>
      <p className="text-sm font-medium">{c.models}</p>
      {node.profiles.map((id, index) => (
        <div className="grid gap-1" key={`${index}-${id}`}>
          <div className="flex gap-2 items-center">
            <span>{index + 1}.</span>
            <Choice
              label={`${c.models} ${index + 1}`}
              labels={labels}
              onChange={next => onChange({ ...node, profiles: node.profiles.map((p, i) => (i === index ? next : p)) })}
              options={[id, ...available]}
              value={id}
            />
            <Button
              aria-label={`${id} ↑`}
              disabled={index === 0}
              onClick={() => {
                const next = [...node.profiles]

                ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                onChange({ ...node, profiles: next })
              }}
              size="icon-sm"
              variant="ghost"
            >
              ↑
            </Button>
            <Button
              onClick={() => onChange({ ...node, profiles: node.profiles.filter(p => p !== id) })}
              variant="ghost"
            >
              {c.remove}
            </Button>
          </div>
          {profiles[id]?.description && <p className="text-xs text-muted-foreground">{profiles[id].description}</p>}
        </div>
      ))}
      <Button
        disabled={!available.length || node.profiles.length >= 32}
        onClick={() => onChange({ ...node, profiles: [...node.profiles, available[0]] })}
        variant="outline"
      >
        {c.addModel}
      </Button>
    </div>
  )
}
