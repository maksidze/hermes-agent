import type { OrchestrationProgressPayload } from '@hermes/shared'

import { recordOrchestrationProgress } from '@/store/orchestration-progress'

import type { GatewayEventContext } from './types'

export function handleOrchestrationEvent({ event, sessionId, deps }: GatewayEventContext): boolean {
  if (event.type !== 'orchestration.progress') {
    return false
  }

  if (sessionId && event.payload && !deps.sessionInterrupted(sessionId)) {
    recordOrchestrationProgress(sessionId, event.payload as OrchestrationProgressPayload)
  }

  return true
}
