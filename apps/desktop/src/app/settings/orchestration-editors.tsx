import { useQuery } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getGlobalModelOptions, type ProfileScope } from '@/hermes'
import { useI18n } from '@/i18n'
import { orchestrationCopy } from '@/i18n/orchestration'
import { graphCopy } from '@/i18n/orchestration-graph'
import { orchestrationLayoutCopy } from '@/i18n/orchestration-layout'

import { ModelSelect } from './model-select'
import { type ExecutionProfile, nextId, type OrchestrationRecord, profileInUse } from './orchestration-data'
import { ListRow, ToggleRow } from './primitives'

export function Choice({
  label,
  value,
  options,
  labels,
  onChange
}: {
  label: string
  value: string
  options: readonly string[]
  labels?: Record<string, string>
  onChange: (value: string) => void
}) {
  return (
    <Select onValueChange={onChange} value={value || '__none__'}>
      <SelectTrigger aria-label={label}>
        <SelectValue className="min-w-0 truncate" placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map(option => (
          <SelectItem key={option || '__none__'} value={option || '__none__'}>
            {labels?.[option] ?? (option || '—')}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

interface EditorProps {
  value: OrchestrationRecord
  onChange: (value: OrchestrationRecord) => void
}

export function ProfileEditor({
  value,
  onChange,
  scope,
  onTest,
  dirty
}: EditorProps & {
  scope?: ProfileScope
  onTest: (id: string) => void
  dirty: boolean
}) {
  const { t, locale } = useI18n()
  const c = { ...orchestrationCopy(locale), ...orchestrationLayoutCopy(locale) }

  const catalog = useQuery({
    queryKey: ['orchestration-model-options', scope],
    queryFn: () => getGlobalModelOptions(undefined, scope)
  })

  const g = graphCopy(locale)
  const providers = catalog.data?.providers ?? []

  const update = (id: string, patch: Partial<ExecutionProfile>) =>
    onChange({ ...value, profiles: { ...value.profiles, [id]: { ...value.profiles[id], ...patch } } })

  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted-foreground">{c.profilesHelp}</p>
      {Object.entries(value.profiles).map(([id, profile]) => {
        const provider = providers.find(row => row.slug === profile.provider)
        const used = profileInUse(value, id)

        return (
          <ProfileDisclosure initiallyOpen={!profile.provider || !profile.model} key={id}>
            <summary className="text-sm">
              <span className="inline-flex max-w-full flex-wrap items-center gap-2 align-middle">
                <span className="font-medium break-all">{id}</span>

                {!profile.enabled && <Badge variant="warn">{c.disabled}</Badge>}
                <span className="text-muted-foreground break-all">{profile.model || c.selectModel}</span>
              </span>
            </summary>
            <div className="grid gap-1 pt-2">
              <ToggleRow checked={profile.enabled} label={id} onChange={enabled => update(id, { enabled })} />
              <ListRow
                action={
                  <Choice
                    label={`${id} provider`}
                    onChange={providerId => update(id, { provider: providerId, model: '' })}
                    options={providers.map(row => row.slug)}
                    value={profile.provider}
                  />
                }
                title={t.settings.model.provider}
              />
              <ListRow
                action={
                  <ModelSelect
                    aria-label={`${id} model`}
                    models={provider?.models ?? []}
                    onValueChange={model => update(id, { model })}
                    provider={provider}
                    providerSlug={profile.provider}
                    value={profile.model}
                  />
                }
                title={t.settings.model.model}
              />
              <ListRow
                action={
                  <Input
                    aria-label={`${id} description`}
                    maxLength={1000}
                    onChange={event => update(id, { description: event.target.value })}
                    value={profile.description ?? ''}
                  />
                }
                description={g.modelHelp}
                title={g.description}
              />
              <details>
                <summary className="text-sm text-muted-foreground">{c.advanced}</summary>
                <ListRow
                  action={
                    <Input
                      aria-label={`${id} id`}
                      defaultValue={id}
                      disabled={used}
                      onBlur={event => {
                        const name = event.target.value.trim()

                        if (
                          name === id ||
                          !/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(name) ||
                          Object.hasOwn(value.profiles, name)
                        ) {
                          return
                        }

                        const profiles = { ...value.profiles, [name]: profile }
                        delete profiles[id]
                        onChange({ ...value, profiles })
                      }}
                    />
                  }
                  title={c.profileId}
                />
                <ListRow
                  action={
                    <Choice
                      label={`${id} reasoning`}
                      onChange={effort => update(id, { reasoning_effort: effort === '__none__' ? undefined : effort })}
                      options={['', 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']}
                      value={profile.reasoning_effort ?? ''}
                    />
                  }
                  title={c.reasoning}
                />
                {(['max_parallel'] as const).map(field => (
                  <ListRow
                    action={
                      <Input
                        aria-label={`${id} ${field}`}
                        min={1}
                        onChange={event => update(id, { [field]: Number(event.target.value) })}
                        type="number"
                        value={profile[field] ?? 1}
                      />
                    }
                    key={field}
                    title={c.parallel}
                  />
                ))}
                {(['tools', 'vision', 'structured_output'] as const).map(capability => (
                  <ListRow
                    action={
                      <Choice
                        label={`${id} ${capability}`}
                        onChange={selected =>
                          update(id, {
                            capabilities: {
                              ...profile.capabilities,
                              [capability]: selected === 'auto' ? 'auto' : selected === 'true'
                            }
                          })
                        }
                        options={['auto', 'true', 'false']}
                        value={String(profile.capabilities?.[capability] ?? 'auto')}
                      />
                    }
                    key={capability}
                    title={{ tools: c.tools, vision: c.vision, structured_output: c.structured }[capability]}
                  />
                ))}
              </details>
              <div className="flex flex-wrap gap-2">
                <Button disabled={dirty} onClick={() => onTest(id)} size="sm" variant="outline">
                  {c.test}
                </Button>
                <Button
                  disabled={used}
                  onClick={() => {
                    const profiles = { ...value.profiles }
                    delete profiles[id]
                    onChange({ ...value, profiles })
                  }}
                  size="sm"
                  variant="ghost"
                >
                  {t.common.remove}
                </Button>
              </div>
              {dirty && <p className="text-xs text-muted-foreground">{c.saveFirst}</p>}
              {used && <p className="text-xs text-muted-foreground">{c.inUse}</p>}
            </div>
          </ProfileDisclosure>
        )
      })}
      {catalog.isError && (
        <Button onClick={() => void catalog.refetch()} variant="outline">
          {c.refresh}
        </Button>
      )}
      <Button
        onClick={() => {
          const id = nextId(value.profiles, 'profile')
          onChange({
            ...value,
            profiles: {
              ...value.profiles,
              [id]: { enabled: true, provider: '', model: '', level: 'fast', max_parallel: 1 }
            }
          })
        }}
        size="sm"
        variant="outline"
      >
        {c.addProfile}
      </Button>
    </div>
  )
}

function ProfileDisclosure({ initiallyOpen, children }: { initiallyOpen: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(initiallyOpen)

  return (
    <details className="py-2" onToggle={event => setOpen(event.currentTarget.open)} open={open}>
      {children}
    </details>
  )
}
