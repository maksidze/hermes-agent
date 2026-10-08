import { useStore } from '@nanostores/react'
import { type ReactNode, useMemo, useState } from 'react'

import { hermesConfigCacheWriter, hermesConfigKey, useHermesConfigRecord } from '@/app/hooks/use-config-record'
import type { OrchestrationRecord } from '@/app/settings/orchestration-data'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { saveHermesConfig } from '@/hermes'
import { useI18n } from '@/i18n'
import { orchestrationChatCopy } from '@/i18n/orchestration-chat'
import { ChevronDown } from '@/lib/icons'
import { queryClient } from '@/lib/query-client'
import { $activeConnectionId } from '@/store/connections'
import { $activeGatewayProfile } from '@/store/profile'

import { mergeOrchestration, orchestrationPatch } from './orchestration-options'
import { useComposerScope } from './scope'

export function OrchestrationPill({ disabled, children }: { disabled: boolean; children?: ReactNode }) {
  const owner = useComposerScope()
  const connectionId = useStore($activeConnectionId)
  const profile = useStore($activeGatewayProfile)

  const scope = useMemo(
    () => ({ connectionId: owner.connectionId ?? connectionId, profile: owner.profile ?? profile ?? 'default' }),
    [connectionId, profile, owner.connectionId, owner.profile]
  )

  return (
    <ScopedOrchestration disabled={disabled} key={`${scope.connectionId}:${scope.profile}`} scope={scope}>
      {children}
    </ScopedOrchestration>
  )
}

interface Props {
  children?: ReactNode
  disabled: boolean
  scope: { connectionId: string | null; profile: string }
}

function ScopedOrchestration({ disabled, scope, children }: Props) {
  const { locale } = useI18n()
  const c = orchestrationChatCopy(locale)
  const query = useHermesConfigRecord(scope)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const config = query.data?.orchestration as OrchestrationRecord | undefined
  const write = useMemo(() => hermesConfigCacheWriter(scope), [scope])

  if (!config || !Object.keys(config.profiles ?? {}).length) {
    return children
  }

  const enabled = !!config.enabled
  const route = config.routing?.default_route ?? Object.keys(config.routes)[0] ?? 'general'
  const label = c.title

  const save = async (patch: Partial<OrchestrationRecord>) => {
    setError('')
    setBusy(true)
    const previous = config
    const writeScope = query.writeScope ?? scope

    try {
      await queryClient.cancelQueries({ queryKey: hermesConfigKey(scope) })
      write(record => (record ? { ...record, orchestration: mergeOrchestration(previous, patch) } : record))
      await saveHermesConfig({ orchestration: patch }, writeScope)
    } catch (cause) {
      write(record => (record ? { ...record, orchestration: previous } : record))
      setError(String(cause))
      void query.refetch()
    } finally {
      setBusy(false)
    }
  }

  const choose = (on: boolean, selected?: string) => {
    try {
      void save(orchestrationPatch(config, on, selected))
    } catch (cause) {
      setError(String(cause))
    }
  }

  return (
    <>
      {!enabled && children}
      <div className="flex min-w-0 items-center gap-1">
        <Button
          aria-checked={enabled}
          aria-label={label}
          disabled={disabled || busy}
          onClick={() => choose(!enabled)}
          role="switch"
          size="sm"
          title={c.scope}
          type="button"
          variant="ghost"
        >
          {label}: {enabled ? c.on : c.off}
        </Button>
        <DropdownMenu
          onOpenChange={open => {
            if (open) {
              void query.refetch()
            }
          }}
        >
          <DropdownMenuTrigger asChild>
            <Button aria-label={c.selection} disabled={disabled || busy} size="sm" type="button" variant="ghost">
              {route}
              <ChevronDown className="size-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="top">
            <DropdownMenuLabel>{c.team}</DropdownMenuLabel>
            <DropdownMenuRadioGroup
              onValueChange={selected => {
                if (enabled) {
                  choose(true, selected)
                } else {
                  void save({ routing: { default_route: selected } })
                }
              }}
              value={route}
            >
              {Object.keys(config.routes).map(id => (
                <DropdownMenuRadioItem key={id} value={id}>
                  {id}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>{c.architect}</DropdownMenuLabel>
            <DropdownMenuRadioGroup
              onValueChange={planner_profile => void save({ automation: { planner_profile } })}
              value={config.automation?.planner_profile ?? ''}
            >
              {Object.entries(config.profiles).map(([id, p]) => (
                <DropdownMenuRadioItem disabled={!p.enabled} key={id} value={id}>
                  {id} · {p.model}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
        {error && (
          <span className="text-xs text-destructive" role="alert">
            {error}
          </span>
        )}
      </div>
    </>
  )
}
