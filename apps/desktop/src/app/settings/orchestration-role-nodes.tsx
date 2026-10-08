import { Handle, type Node, type NodeProps, Position } from '@xyflow/react'

import { useI18n } from '@/i18n'
import { roleCopy } from '@/i18n/orchestration-roles'

import type { OrchestrationRecord } from './orchestration-data'
import { Choice } from './orchestration-editors'
import { ListRow, ToggleRow } from './primitives'

export const PLANNER_NODE = '__planner'
interface PlanningData extends Record<string, unknown> {
  config: OrchestrationRecord
  route: string
  onChange: (value: OrchestrationRecord) => void
}
export type PlanningNode = Node<PlanningData, 'planning'>

export function Planning({ data }: NodeProps<PlanningNode>) {
  const { locale } = useI18n()
  const c = roleCopy(locale)
  const value = data.config
  const fallback = [...(value.routes[data.route] ?? [])].reverse().find(id => value.profiles[id]?.enabled)
  const chosen = value.automation?.planner_profile || fallback

  return (
    <div className="orchestration-pool">
      <div className="orchestration-pool-title">{c.planning}</div>
      <div className="orchestration-pool-models nodrag nopan nowheel">
        <span>{c.planner}</span>
        <Choice
          label={c.planner}
          labels={{
            '': c.auto,
            ...Object.fromEntries(Object.entries(value.profiles).map(([id, p]) => [id, `${p.model} · ${id}`]))
          }}
          onChange={id =>
            data.onChange({
              ...value,
              automation: { ...value.automation, planner_profile: id === '__none__' ? '' : id }
            })
          }
          options={['', ...Object.keys(value.profiles).filter(id => value.profiles[id].enabled)]}
          value={value.automation?.planner_profile ?? ''}
        />
        <ToggleRow
          checked={value.routing?.adaptive_entry !== false}
          label={c.adaptive}
          onChange={adaptive_entry => data.onChange({ ...value, routing: { ...value.routing, adaptive_entry } })}
        />
        <p className="text-muted-foreground">{c.adaptiveHelp}</p>
        <p>{chosen ? value.profiles[chosen]?.model || chosen : c.missing}</p>
      </div>
      <div className="orchestration-port success">
        {value.routing?.adaptive_entry === false ? c.plan : c.adaptivePlan}
        <Handle id="plan" isConnectable={value.routing?.adaptive_entry !== false} position={Position.Right} type="source" />
      </div>
    </div>
  )
}

export function reviewLabel(value: OrchestrationRecord, locale: string): string {
  const c = roleCopy(locale)

  if (value.verification?.semantic === 'off') {
    return `${c.mode}: ${c.modes.off}`
  }

  const id = value.verification?.verifier_profile

  return `${c.reviewer}: ${id ? value.profiles[id]?.model || id : c.missing}`
}

export function ReviewSettings({
  value,
  onChange
}: {
  value: OrchestrationRecord
  onChange: (value: OrchestrationRecord) => void
}) {
  const { locale } = useI18n()
  const c = roleCopy(locale)

  return (
    <div className="grid gap-2">
      <p className="text-sm text-muted-foreground">{c.help}</p>
      <ListRow
        action={
          <Choice
            label={c.reviewer}
            labels={{
              '': c.missing,
              ...Object.fromEntries(Object.entries(value.profiles).map(([id, p]) => [id, `${p.model} · ${id}`]))
            }}
            onChange={id =>
              onChange({
                ...value,
                verification: { ...value.verification, verifier_profile: id === '__none__' ? '' : id }
              })
            }
            options={['', ...Object.keys(value.profiles).filter(id => value.profiles[id].enabled)]}
            value={value.verification?.verifier_profile ?? ''}
          />
        }
        title={c.reviewer}
      />
      <ListRow
        action={
          <Choice
            label={c.mode}
            labels={c.modes}
            onChange={semantic => onChange({ ...value, verification: { ...value.verification, semantic } })}
            options={['off', 'risk_based', 'always']}
            value={value.verification?.semantic ?? 'risk_based'}
          />
        }
        description={c.checks}
        title={c.mode}
      />
    </div>
  )
}
