import { graphError } from './orchestration-graph-data'

export interface ExecutionProfile {
  enabled: boolean
  provider: string
  model: string
  level: string
  description?: string
  reasoning_effort?: string
  max_parallel?: number
  priority?: number
  capabilities?: Record<string, boolean | string>
}

export interface OrchestrationRecord {
  enabled?: boolean
  mode?: string
  profiles: Record<string, ExecutionProfile>
  routes: Record<string, string[]>
  graphs?: Record<string, RouteGraph>
  specializations?: Record<string, Specialization>
  routing?: { default_route?: string; preferred_profile?: string; adaptive_entry?: boolean }
  automation?: { mode?: string; planner_profile?: string; max_tasks?: number }
  workspace?: { enabled?: boolean; apply_on_success?: boolean }
  budget?: Record<string, number>
  verification?: { verifier_profile?: string; semantic?: string; deterministic?: boolean }
  [key: string]: unknown
}

export type GraphOutcome = 'success' | 'failure' | 'unavailable' | 'uncertain'
export interface RouteNode {
  id: string
  label: string
  description?: string
  profiles: string[]
  position: { x: number; y: number }
}
export interface RouteGraph {
  entry: string
  entry_nodes?: string[]
  nodes: RouteNode[]
  edges: { source: string; target: string; on: GraphOutcome }[]
}

export interface Specialization {
  enabled: boolean
  description: string
  route: string
  local_only: boolean
  planner_profile?: string
  verifier_profile?: string
  isolate_workspace?: boolean
}

export const ORCHESTRATION_KEYS = [
  'enabled',
  'automation.planner_profile',
  'automation.max_tasks',
  'workspace.enabled',
  'workspace.apply_on_success',
  'routing.preferred_profile',
  'routing.strategy',
  'routing.default_route',
  'routing.default_level',
  'routing.allow_direct_deep',
  'routing.max_specialist_switches',
  'profiles',
  'routes',
  'graphs',
  'specializations',
  'escalation.enabled',
  'escalation.same_profile_repairs',
  'escalation.max_escalations',
  'escalation.triggers.verification_failed',
  'escalation.triggers.schema_failed',
  'escalation.triggers.repetition_detected',
  'escalation.triggers.explicit_request',
  'verification.deterministic',
  'verification.semantic',
  'verification.verifier_profile',
  'verification.uncertain_action',
  'verification.main_agent_stop_gate',
  'budget.max_attempts',
  'budget.max_escalations',
  'budget.max_model_calls',
  'budget.max_calls_per_attempt',
  'budget.max_parallel_tasks',
  'budget.timeout_seconds',
  'availability.cache_seconds',
  'availability.failure_cooldown_seconds',
  'privacy.cloud_allowed',
  'logging.decisions',
  'logging.attempts',
  'logging.verification'
].map(key => `orchestration.${key}`)

export function profileInUse(config: OrchestrationRecord, id: string): boolean {
  return (
    Object.values(config.routes).some(route => route.includes(id)) ||
    Object.values(config.graphs ?? {}).some(graph => graph.nodes.some(node => node.profiles.includes(id))) ||
    config.verification?.verifier_profile === id ||
    config.automation?.planner_profile === id ||
    config.routing?.preferred_profile === id ||
    Object.values(config.specializations ?? {}).some(c => c.planner_profile === id || c.verifier_profile === id)
  )
}

export function validOrchestration(config: OrchestrationRecord): boolean {
  if (Object.values(config.graphs ?? {}).some(graph => graphError(graph, config.profiles, config.routing?.adaptive_entry !== false))) {
    return false
  }

  const levels = ['fast', 'balanced', 'deep']
  const identifier = /^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/

  if (
    Object.entries(config.profiles).some(
      ([id, p]) => !identifier.test(id) || !p.provider || !p.model || (p.level && !levels.includes(p.level))
    )
  ) {
    return false
  }

  if (config.verification?.verifier_profile && !config.profiles[config.verification.verifier_profile]) {
    return false
  }

  if (config.automation?.planner_profile && !config.profiles[config.automation.planner_profile]) {
    return false
  }

  if (config.routing?.preferred_profile && !config.profiles[config.routing.preferred_profile]) {
    return false
  }

  if (config.enabled && !config.routes[config.routing?.default_route ?? 'general']) {
    return false
  }

  const categories = Object.entries(config.specializations ?? {})

  if (
    categories.length > 12 ||
    categories.some(
      ([id, c]) =>
        !identifier.test(id) ||
        !c.description.trim() ||
        c.description.length > 500 ||
        !config.routes[c.route] ||
        (c.planner_profile && !config.profiles[c.planner_profile]) ||
        (c.verifier_profile && !config.profiles[c.verifier_profile])
    )
  ) {
    return false
  }

  return Object.entries(config.routes).every(
    ([id, route]) =>
      identifier.test(id) &&
      route.length > 0 &&
      new Set(route).size === route.length &&
      route.every(profile => !!config.profiles[profile])
  )
}

export function nextId(existing: Record<string, unknown>, prefix: string): string {
  let index = 1

  while (Object.hasOwn(existing, `${prefix}_${index}`)) {
    index += 1
  }

  return `${prefix}_${index}`
}
