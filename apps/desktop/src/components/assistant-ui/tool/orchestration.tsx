import type { OrchestrationProgressEntry } from '@hermes/shared'
import { useStore } from '@nanostores/react'

import { useSessionView } from '@/app/chat/session-view'
import type { GraphOutcome } from '@/app/settings/orchestration-data'
import { useI18n } from '@/i18n'
import { graphCopy } from '@/i18n/orchestration-graph'
import { orchestrationProgressCopy } from '@/i18n/orchestration-progress'
import { useSessionSlice } from '@/lib/use-session-slice'
import { $orchestrationProgress } from '@/store/orchestration-progress'

import { parseMaybeObject, type ToolPart } from './fallback-model'
import { ProgressImage } from './result-images'

interface OrchestrationToolProps extends Pick<ToolPart, 'result' | 'toolCallId' | 'toolResultMetadata'> {
  completedAt?: number
}

export function OrchestrationTool({ result, toolCallId, completedAt, toolResultMetadata }: OrchestrationToolProps) {
  const sessionId = useStore(useSessionView().$runtimeId)
  const live = useSessionSlice($orchestrationProgress, sessionId).find(row => row.tool_id === toolCallId)
  const { locale } = useI18n()
  const c = orchestrationProgressCopy(locale)
  const graph = graphCopy(locale)
  const output = { ...toolResultMetadata?.orchestration, ...parseMaybeObject(result) }

  const rows = (
    Array.isArray(output.timeline) ? output.timeline : (live?.entries ?? [])
  ) as OrchestrationProgressEntry[]

  const settled = result !== undefined || completedAt !== undefined
  const status = settled ? (output.status === 'completed' ? c.completed : c.stopped) : c.running
  const journal = typeof output.progress_journal === 'string' ? output.progress_journal : live?.journal

  return (
    <section aria-label={c.title} className="my-2 grid min-w-0 gap-2 text-sm" data-slot="tool-block">
      <div className="font-medium">
        {c.title} · {status}
      </div>
      <ol className="grid min-w-0 gap-2">
        {rows
          .filter(row => !['task_state_changed', 'plan_created', 'attempt_completed'].includes(row.event))
          .map((row, index) => (
            <li className="min-w-0" key={`${row.time}-${index}`}>
              <div className="text-(--ui-text-secondary)">
                <time>{new Date(row.time * 1000).toLocaleTimeString(locale)}</time>
                {' · '}
                {c.events[row.event] ?? row.event}
                {row.fields?.role && ` · ${c.roles[row.fields.role] ?? row.fields.role}`}
                {row.fields?.route && ` · ${row.fields.route}`}
                {row.event === 'entry_selected' && row.fields?.node && ` · ${row.fields.node}`}
                {row.fields?.level && row.fields.level !== 'graph' && ` · ${row.fields.level}`}
                {row.fields?.profile && ` · ${row.fields.profile}`}
                {row.fields?.model && ` (${row.fields.model})`}
                {row.fields?.attempt && ` #${row.fields.attempt}`}
              </div>
              {(row.detail || row.fields?.reason) && (
                <div className="whitespace-pre-wrap break-words">
                  {row.event === 'graph_transition'
                    ? `${row.fields.node} → ${row.fields.target} · ${graph.outcomes[row.fields.reason as GraphOutcome] ?? row.fields.reason}`
                    : c.reasons[row.detail || row.fields.reason] ?? (row.detail || row.fields.reason)}
                </div>
              )}
              <ProgressImage event={row.event} fields={row.fields} />
            </li>
          ))}
      </ol>
      {typeof output.reason === 'string' && (
        <p className="text-destructive">{c.reasons[output.reason] ?? output.reason}</p>
      )}
      {journal && (
        <p className="break-all text-xs text-(--ui-text-tertiary)">
          {c.journal}: {journal}
        </p>
      )}
    </section>
  )
}
