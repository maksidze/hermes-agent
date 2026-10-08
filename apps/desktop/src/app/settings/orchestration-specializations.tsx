import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/i18n'
import { specializationCopy } from '@/i18n/orchestration-specializations'

import { nextId, type OrchestrationRecord, type Specialization } from './orchestration-data'
import { Choice } from './orchestration-editors'
import { ListRow, ToggleRow } from './primitives'

export function categoryTemplates(locale: string, route: string): Record<string, Specialization> {
  const c = specializationCopy(locale)

  return Object.fromEntries(
    [
      ['reverse_engineering', c.reverse, false, true],
      ['roleplay', c.roleplay, false, false],
      ['sensitive_analysis', c.sensitive, false, false],
      ['local_private', c.private, true, true]
    ].map(([id, description, local_only, isolate_workspace]) => [
      id,
      {
        enabled: false,
        description,
        route,
        local_only,
        isolate_workspace
      }
    ])
  ) as Record<string, Specialization>
}

interface Props {
  value: OrchestrationRecord
  onChange: (value: OrchestrationRecord) => void
}

export function SpecializationEditor({ value, onChange }: Props) {
  const { t, locale } = useI18n()
  const c = specializationCopy(locale)
  const categories = value.specializations ?? {}
  const routes = Object.keys(value.routes)
  const profiles = Object.keys(value.profiles)
  const route = value.routing?.default_route ?? routes[0] ?? ''
  const change = (specializations: Record<string, Specialization>) => onChange({ ...value, specializations })

  const update = (id: string, patch: Partial<Specialization>) =>
    change({ ...categories, [id]: { ...categories[id], ...patch } })

  return (
    <div className="grid gap-6">
      <p className="text-sm text-muted-foreground">{c.intro}</p>
      <p className="text-sm text-muted-foreground">{c.automatic}</p>
      <p className="text-sm text-muted-foreground">{c.setup}</p>
      {!routes.length && <p>{c.emptyRoute}</p>}
      <Button
        disabled={!routes.length || Object.keys({ ...categoryTemplates(locale, route), ...categories }).length > 12}
        onClick={() => change({ ...categoryTemplates(locale, route), ...categories })}
        variant="outline"
      >
        {c.templates}
      </Button>
      {Object.entries(categories).map(([id, category]) => (
        <div className="grid gap-3" key={id}>
          <ToggleRow checked={category.enabled} label={id} onChange={enabled => update(id, { enabled })} />
          <Input
            aria-label={`${id} id`}
            defaultValue={id}
            onBlur={event => {
              const name = event.target.value.trim()

              if (name === id || !/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(name) || Object.hasOwn(categories, name)) {return}
              const next = { ...categories, [name]: category }
              delete next[id]
              change(next)
            }}
          />
          <p className="text-sm">
            {c.prefix} <code>@{id}</code>
          </p>
          <label className="grid gap-2 text-sm">
            {c.description}
            <Textarea
              aria-label={`${id} description`}
              maxLength={500}
              onChange={event => update(id, { description: event.target.value })}
              value={category.description}
            />
          </label>
          <ListRow
            action={
              <Choice
                label={`${id} route`}
                onChange={selected => update(id, { route: selected })}
                options={routes}
                value={category.route}
              />
            }
            title={c.route}
          />
          {(['planner_profile', 'verifier_profile'] as const).map(role => (
            <ListRow
              action={
                <Choice
                  label={`${id} ${role}`}
                  labels={{ '': category.local_only ? c.localDefault : c.inherit }}
                  onChange={selected => update(id, { [role]: selected === '__none__' ? '' : selected })}
                  options={['', ...profiles]}
                  value={category[role] ?? ''}
                />
              }
              key={role}
              title={role === 'planner_profile' ? c.planner : c.verifier}
            />
          ))}
          <ToggleRow
            checked={category.local_only}
            label={c.local}
            onChange={local_only => update(id, { local_only })}
          />
          {category.local_only && <p className="text-sm text-muted-foreground">{c.localHint}</p>}
          <ToggleRow
            checked={category.isolate_workspace ?? !!value.workspace?.enabled}
            label={c.workspace}
            onChange={isolate_workspace => update(id, { isolate_workspace })}
          />
          <p className="text-xs text-muted-foreground">{c.workspaceHint}</p>
          <Button
            onClick={() => {
              const next = { ...categories }
              delete next[id]
              change(next)
            }}
            variant="ghost"
          >
            {t.common.remove}
          </Button>
        </div>
      ))}
      <Button
        disabled={!routes.length || Object.keys(categories).length >= 12}
        onClick={() =>
          change({
            ...categories,
            [nextId(categories, 'specialist')]: { enabled: false, description: '', route, local_only: false }
          })
        }
        variant="outline"
      >
        {c.custom}
      </Button>
    </div>
  )
}
