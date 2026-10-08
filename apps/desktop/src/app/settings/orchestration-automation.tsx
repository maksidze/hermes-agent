import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n'
import { automationCopy } from '@/i18n/orchestration-automation'

import type { OrchestrationRecord } from './orchestration-data'
import { Choice } from './orchestration-editors'
import { ListRow, ToggleRow } from './primitives'

export function recommendedSetup(value: OrchestrationRecord): OrchestrationRecord {
  const entries = Object.entries(value.profiles).filter(([, p]) => p.enabled)
  const pick = (level: string) => entries.find(([, p]) => p.level === level)?.[0] ?? entries[0]?.[0] ?? ''

  return {
    ...value,
    enabled: true,
    mode: 'auto',
    automation: { ...value.automation, mode: 'all', planner_profile: pick('deep'), max_tasks: 6 },
    routing: { ...value.routing, default_route: value.routing?.default_route ?? Object.keys(value.routes)[0] },
    verification: { ...value.verification, verifier_profile: pick('balanced') },
    workspace: { enabled: true, apply_on_success: true },
    budget: {
      ...value.budget,
      max_attempts: Math.max(value.budget?.max_attempts ?? 0, 16),
      max_model_calls: Math.max(value.budget?.max_model_calls ?? 0, 80),
      max_calls_per_attempt: value.budget?.max_calls_per_attempt ?? 12,
      timeout_seconds: Math.max(value.budget?.timeout_seconds ?? 0, 1200)
    }
  }
}

export function AutomationSetup({
  value,
  onChange
}: {
  value: OrchestrationRecord
  onChange: (value: OrchestrationRecord) => void
}) {
  const { locale } = useI18n()
  const c = automationCopy(locale)
  const profiles = Object.keys(value.profiles).filter(id => value.profiles[id].enabled)
  const routes = Object.keys(value.routes)
  const labels = Object.fromEntries(profiles.map(id => [id, `${value.profiles[id].model} (${id})`]))

  return (
    <div className="mb-6">
      <p className="font-medium">{c.title}</p>
      <p className="my-3 text-sm text-muted-foreground">{c.description}</p>
      <Button
        disabled={!profiles.length || !routes.length}
        onClick={() => onChange(recommendedSetup(value))}
        variant="outline"
      >
        {c.setup}
      </Button>
      {(!profiles.length || !routes.length) && <p className="mt-2 text-sm text-muted-foreground">{c.missing}</p>}
      <ToggleRow checked={!!value.enabled} label={c.enabled} onChange={enabled => onChange({ ...value, enabled })} />
      <p className="my-3 text-sm text-muted-foreground">{c.detection}</p>
      <ListRow
        action={
          <Choice
            label={c.architect}
            labels={labels}
            onChange={id =>
              onChange({ ...value, automation: { ...value.automation, planner_profile: id === '__none__' ? '' : id } })
            }
            options={['', ...profiles]}
            value={value.automation?.planner_profile ?? ''}
          />
        }
        description={c.architectHelp}
        title={c.architect}
      />
      <ListRow
        action={
          <Choice
            label={c.workers}
            onChange={default_route => onChange({ ...value, routing: { ...value.routing, default_route } })}
            options={routes}
            value={value.routing?.default_route ?? 'general'}
          />
        }
        description={c.workersHelp}
        title={c.workers}
      />
      <ListRow
        action={
          <Choice
            label={c.reviewer}
            labels={labels}
            onChange={id =>
              onChange({
                ...value,
                verification: { ...value.verification, verifier_profile: id === '__none__' ? '' : id }
              })
            }
            options={['', ...profiles]}
            value={value.verification?.verifier_profile ?? ''}
          />
        }
        description={c.reviewerHelp}
        title={c.reviewer}
      />
      <ToggleRow
        checked={!!value.workspace?.enabled}
        description={c.isolationHelp}
        label={c.isolation}
        onChange={enabled => onChange({ ...value, workspace: { ...value.workspace, enabled } })}
      />
      <ToggleRow
        checked={value.workspace?.apply_on_success !== false}
        description={c.applyHelp}
        label={c.apply}
        onChange={apply_on_success => onChange({ ...value, workspace: { ...value.workspace, apply_on_success } })}
      />
      <ListRow
        action={
          <Choice
            label={c.preferred}
            labels={{ ...labels, '': c.automatic }}
            onChange={id =>
              onChange({ ...value, routing: { ...value.routing, preferred_profile: id === '__none__' ? '' : id } })
            }
            options={['', ...profiles]}
            value={value.routing?.preferred_profile ?? ''}
          />
        }
        description={c.preferredHelp}
        title={c.preferred}
      />
    </div>
  )
}
