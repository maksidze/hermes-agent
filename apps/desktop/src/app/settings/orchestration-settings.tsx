import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import { Fragment, type ReactNode, useMemo, useState } from 'react'

import { capabilityScoped, type ProfileScope } from '@/api/client'
import { Button } from '@/components/ui/button'
import { getHermesConfigSchema, saveHermesConfig } from '@/hermes'
import { useI18n } from '@/i18n'
import { orchestrationCopy } from '@/i18n/orchestration'
import { automationCopy } from '@/i18n/orchestration-automation'
import { $activeConnectionId } from '@/store/connections'
import { $activeGatewayProfile } from '@/store/profile'
import type { ConfigFieldSchema, HermesConfigRecord } from '@/types/hermes'

import { hermesConfigCacheWriter, useHermesConfigRecord } from '../hooks/use-config-record'

import { ConfigField } from './config-field'
import { configSubpageForField } from './config-subpages'
import { getNested, setNested } from './helpers'
import { AutomationSetup } from './orchestration-automation'
import { type OrchestrationRecord, validOrchestration } from './orchestration-data'
import { ProfileEditor } from './orchestration-editors'
import { RouteEditor } from './orchestration-graph-editor'
import { SpecializationEditor } from './orchestration-specializations'
import { SettingsContent, SettingsSkeleton } from './primitives'
import { SettingsProfileScope } from './profile-scope'

interface Props {
  scopeProfile?: string
  subpage?: string
  onConfigSaved?: () => void
}

export function OrchestrationSettings(props: Props) {
  const activeProfile = useStore($activeGatewayProfile)
  const connection = useStore($activeConnectionId)
  const scope = props.scopeProfile ?? activeProfile ?? 'default'

  return <ScopedSettings {...props} key={`${connection}:${scope}`} scopeProfile={scope} />
}

function ScopedSettings({ scopeProfile, ...props }: Props) {
  const connectionId = useStore($activeConnectionId)
  const pinnedScope = useMemo(() => ({ connectionId, profile: scopeProfile }), [connectionId, scopeProfile])
  const { data, writeScope, isError, refetch } = useHermesConfigRecord(scopeProfile)
  const { t } = useI18n()

  const schema = useQuery({
    queryKey: ['hermes-config-schema', pinnedScope],
    queryFn: () => getHermesConfigSchema(pinnedScope)
  })

  const writer = useMemo(() => hermesConfigCacheWriter(pinnedScope), [pinnedScope])

  if (isError || schema.isError) {
    return (
      <Button
        onClick={() => {
          void refetch()
          void schema.refetch()
        }}
      >
        {t.settings.config.failedLoad}
      </Button>
    )
  }

  if (!data || !schema.data) {
    return <SettingsSkeleton sections={[{ rows: 5 }]} />
  }

  return (
    <OrchestrationEditor
      {...props}
      initial={data}
      onSaved={next => writer(previous => (previous ? { ...previous, orchestration: next.orchestration } : next))}
      schema={schema.data.fields}
      scope={writeScope ?? pinnedScope}
    />
  )
}

interface EditorProps extends Omit<Props, 'scopeProfile'> {
  initial: HermesConfigRecord
  scope?: ProfileScope
  schema: Record<string, ConfigFieldSchema>
  onSaved: (config: HermesConfigRecord) => void
}

function OrchestrationEditor({ initial, scope, schema, subpage = 'general', onSaved, onConfigSaved }: EditorProps) {
  const { t, locale } = useI18n()
  const c = orchestrationCopy(locale)
  const [config, setConfig] = useState(initial)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [probe, setProbe] = useState('')
  const orchestration = (config.orchestration ?? { profiles: {}, routes: {} }) as OrchestrationRecord

  const update = (next: HermesConfigRecord) => {
    setConfig(next)
    setDirty(true)
    setError('')
  }

  const edit = (next: OrchestrationRecord) => update({ ...config, orchestration: next })

  const save = async () => {
    if (!validOrchestration(orchestration)) {
      setError(c.invalid)

      return
    }

    setBusy(true)

    try {
      await saveHermesConfig({ orchestration }, scope)
      onSaved(config)

      setDirty(false)
      onConfigSaved?.()
    } catch (cause) {
      setError(String(cause))
    } finally {
      setBusy(false)
    }
  }

  const test = async (id: string) => {
    setBusy(true)
    setProbe('')

    try {
      const response = await window.hermesDesktop.api<{ status: string }>({
        ...capabilityScoped(scope),
        path: `/api/orchestration/test-profile/${encodeURIComponent(id)}`,
        method: 'POST',
        timeoutMs: 60_000
      })

      setProbe(`${id}: ${response.status}`)
    } catch (cause) {
      setError(String(cause))
    } finally {
      setBusy(false)
    }
  }

  const fields = Object.entries(schema).filter(
    ([key]) =>
      ![
        'orchestration.mode',
        'orchestration.automation.mode',
        'orchestration.routing.default_level',
        'orchestration.routing.allow_direct_deep'
      ].includes(key) && configSubpageForField('orchestration', key) === subpage
  )

  const FieldContainer = subpage === 'general' ? AdvancedFields : Fragment

  return (
    <SettingsContent>
      <SettingsProfileScope className="mb-5" />
      <p className="mb-4 text-sm text-muted-foreground">{c.nextSession}</p>
      <fieldset className="min-w-0" disabled={busy}>
        {subpage === 'general' && <AutomationSetup onChange={edit} value={orchestration} />}
        {subpage === 'profiles' && (
          <ProfileEditor
            dirty={dirty}
            onChange={edit}
            onTest={id => void test(id)}
            scope={scope}
            value={orchestration}
          />
        )}
        {subpage === 'routes' && <RouteEditor onChange={edit} value={orchestration} />}
        {subpage === 'specializations' && <SpecializationEditor onChange={edit} value={orchestration} />}
        <FieldContainer>
          {!['profiles', 'routes', 'specializations'].includes(subpage) &&
            fields.map(([key, field]) => {
              const options =
                key === 'orchestration.routing.default_route'
                  ? Object.keys(orchestration.routes)
                  : [
                        'orchestration.verification.verifier_profile',
                        'orchestration.automation.planner_profile',
                        'orchestration.routing.preferred_profile'
                      ].includes(key)
                    ? ['', ...Object.keys(orchestration.profiles)]
                    : field.options?.map(String)

              return (
                <ConfigField
                  enumOptions={options}
                  key={key}
                  onChange={value => update(setNested(config, key, value))}
                  schema={options ? { ...field, type: 'select' } : field}
                  schemaKey={key}
                  value={getNested(config, key)}
                />
              )
            })}
        </FieldContainer>
        {subpage === 'diagnostics' && <Diagnostics scope={scope} />}
        <div className="mt-6 flex items-center gap-3">
          <Button disabled={!dirty || busy} onClick={() => void save()}>
            {t.common.save}
          </Button>
          {probe && (
            <span className="text-sm" role="status">
              {probe}
            </span>
          )}
        </div>
      </fieldset>
      {error && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </SettingsContent>
  )
}

function AdvancedFields({ children }: { children: ReactNode }) {
  const { locale } = useI18n()

  return (
    <details>
      <summary>{automationCopy(locale).advanced}</summary>
      {children}
    </details>
  )
}

function Diagnostics({ scope }: { scope?: ProfileScope }) {
  const { locale } = useI18n()
  const c = orchestrationCopy(locale)

  const query = useQuery({
    queryKey: ['orchestration-diagnostics', scope],
    queryFn: () =>
      window.hermesDesktop.api<{
        mode: string
        events: Record<string, unknown>[]
        profiles: { id: string; model: string; status: string }[]
      }>({ ...capabilityScoped(scope), path: '/api/orchestration/diagnostics' })
  })

  return (
    <div className="grid gap-3">
      <Button onClick={() => void query.refetch()} variant="outline">
        {c.refresh}
      </Button>
      {query.isError && <p role="alert">{String(query.error)}</p>}
      {query.data && (
        <>
          <p>{query.data.mode}</p>
          {query.data.profiles.map(profile => (
            <p key={profile.id}>
              {profile.id}: {profile.model} — {profile.status}
            </p>
          ))}
          {!query.data.events.length && <p>{c.emptyEvents}</p>}
          {query.data.events
            .slice(-15)
            .reverse()
            .map((event, index) => (
              <pre className="whitespace-pre-wrap text-xs" key={index}>
                {JSON.stringify(event, null, 2)}
              </pre>
            ))}
        </>
      )}
    </div>
  )
}
