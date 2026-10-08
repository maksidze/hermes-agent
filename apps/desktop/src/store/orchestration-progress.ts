import type { OrchestrationProgressPayload } from '@hermes/shared'
import { atom } from 'nanostores'

export const $orchestrationProgress = atom<Record<string, OrchestrationProgressPayload[]>>({})

export function recordOrchestrationProgress(sessionId: string, progress: OrchestrationProgressPayload): void {
  const sessions = $orchestrationProgress.get()
  const rows = sessions[sessionId] ?? []
  const previous = rows.find(row => row.tool_id === progress.tool_id)
  const last = progress.entries.at(-1)?.time ?? 0

  if ((previous?.entries.at(-1)?.time ?? -1) >= last) {
    return
  }
  $orchestrationProgress.set({
    ...sessions,
    [sessionId]: [...rows.filter(row => row.tool_id !== progress.tool_id), progress].slice(-20)
  })
}
