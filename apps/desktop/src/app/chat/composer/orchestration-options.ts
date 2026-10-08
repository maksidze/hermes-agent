import type { OrchestrationRecord } from '@/app/settings/orchestration-data'

export function orchestrationPatch(value: OrchestrationRecord, enabled: boolean, route?: string) {
  if (!enabled) {
    return { enabled: false }
  }

  const profiles = Object.entries(value.profiles)
    .filter(([, p]) => p.enabled)
    .sort(
      ([, a], [, b]) => ['fast', 'balanced', 'deep'].indexOf(a.level) - ['fast', 'balanced', 'deep'].indexOf(b.level)
    )

  if (!profiles.length) {
    throw new Error('Enable an execution profile in Orchestration settings first.')
  }
  const existing = Object.keys(value.routes)

  const chosen =
    route ??
    (value.routing?.default_route && value.routes[value.routing.default_route]
      ? value.routing.default_route
      : existing[0]) ??
    'general'

  const routes = existing.length ? value.routes : { general: profiles.map(([id]) => id) }

  if (!routes[chosen]) {
    throw new Error('Select an existing orchestration route.')
  }
  const members = routes[chosen].filter(id => value.profiles[id]?.enabled)

  if (!members.length) {
    throw new Error('Enable an execution profile in the selected route first.')
  }

  return {
    enabled: true,
    ...(!existing.length ? { routes } : {}),
    routing: { default_route: chosen },
    automation: { planner_profile: value.automation?.planner_profile || members.at(-1)! },
    verification: { verifier_profile: value.verification?.verifier_profile || members.at(-1)! }
  }
}

export function mergeOrchestration(
  value: OrchestrationRecord,
  patch: Partial<OrchestrationRecord>
): OrchestrationRecord {
  return {
    ...value,
    ...patch,
    routing: { ...value.routing, ...patch.routing },
    automation: { ...value.automation, ...patch.automation },
    verification: { ...value.verification, ...patch.verification }
  }
}
