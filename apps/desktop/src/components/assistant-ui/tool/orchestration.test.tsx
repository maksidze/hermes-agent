import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, expect, it, vi } from 'vitest'

import { applyStoredToolResultToParts, upsertToolPart } from '@/lib/chat-messages/tool-parts'
import { resolveGatewayEventSessionId } from '@/lib/gateway-events'
import { $orchestrationProgress, recordOrchestrationProgress } from '@/store/orchestration-progress'
import type { SessionMessage } from '@/types/hermes'

import { OrchestrationTool } from './orchestration'

const runtimeId = atom<string | null>('owner')
vi.mock('@/app/chat/session-view', () => ({ useSessionView: () => ({ $runtimeId: runtimeId }) }))
vi.mock('@/i18n', () => ({ useI18n: () => ({ locale: 'ru', t: { assistant: { tool: { outputAlt: 'Изображение' } } } }) }))
vi.mock('@/components/assistant-ui/markdown-text', () => ({ MarkdownImage: ({ src, alt }: { src: string; alt: string }) => <img alt={alt} src={src} /> }))

const entry = {
  event: 'escalation_started',
  time: 1,
  detail: 'Проверка выявила ошибку',
  fields: { profile: 'balanced', model: 'model-b' }
}

const progress = { tool_id: 'call-1', entries: [entry], journal: 'D:/test/progress.jsonl' }

it('shows a collapsed MCP image in live progress and after restoring the result', () => {
  const imageEntry = { ...entry, event: 'tool_image', detail: 'mcp__editor__preview', fields: { image_path: '/tmp/preview.png' } }
  const view = render(<OrchestrationTool toolCallId="call-1" />)
  act(() => recordOrchestrationProgress('owner', { ...progress, entries: [imageEntry] }))
  expect(screen.queryByRole('img')).toBeNull()
  fireEvent.click(screen.getByRole('button', { expanded: false }))
  expect(screen.getByRole('img').getAttribute('src')).toBe('/tmp/preview.png')
  view.unmount()
  act(() => $orchestrationProgress.set({}))
  render(<OrchestrationTool result={{ status: 'completed', timeline: [imageEntry] }} toolCallId="call-1" />)
  expect(screen.queryByRole('img')).toBeNull()
  fireEvent.click(screen.getByRole('button', { expanded: false }))
  expect(screen.getByRole('img')).toBeTruthy()
})

afterEach(() => {
  cleanup()
  $orchestrationProgress.set({})
  runtimeId.set('owner')
})

it('shows live transfers only in the owning call and keeps them after completion and reload', () => {
  const view = render(<OrchestrationTool toolCallId="call-1" />)
  act(() => recordOrchestrationProgress('other-session', progress))
  expect(screen.queryByText('Проверка выявила ошибку')).toBeNull()
  act(() => recordOrchestrationProgress('owner', { ...progress, tool_id: 'other-call' }))
  expect(screen.queryByText('Проверка выявила ошибку')).toBeNull()
  act(() => recordOrchestrationProgress('owner', progress))
  expect(screen.getByText(/Смена модели/)).toBeTruthy()
  expect(screen.getByText('Проверка выявила ошибку')).toBeTruthy()

  const metadata = {
    status: 'blocked',
    reason: 'max_model_calls',
    timeline: [entry],
    progress_journal: progress.journal
  }

  const parts = upsertToolPart(
    [],
    { name: 'orchestrate_task', tool_id: 'call-1', args: { goal: 'Site' } },
    'running',
    1
  )

  const restored = applyStoredToolResultToParts(parts, {
    role: 'tool',
    tool_call_id: 'call-1',
    content: 'Large result saved to disk',
    timestamp: 2,
    display_metadata: { tool_result_metadata: { orchestration: metadata } }
  } as SessionMessage)

  const part = restored?.[0]

  if (part?.type !== 'tool-call') {
    throw new Error('Missing restored tool')
  }

  act(() => $orchestrationProgress.set({}))
  view.rerender(<OrchestrationTool {...part} />)
  expect(screen.getByText('Оркестрация · Остановлена')).toBeTruthy()
  expect(screen.getByText('Проверка выявила ошибку')).toBeTruthy()
  expect(screen.getByText(/D:\/test\/progress.jsonl/)).toBeTruthy()
})

it('ignores stale replay and refuses to attribute unscoped progress to the focused chat', () => {
  recordOrchestrationProgress('owner', { ...progress, entries: [{ ...entry, time: 2, detail: 'Newest' }] })
  recordOrchestrationProgress('owner', progress)
  expect($orchestrationProgress.get().owner[0].entries[0].detail).toBe('Newest')
  expect(
    resolveGatewayEventSessionId({
      activeSessionId: 'focused',
      eventType: 'orchestration.progress',
      explicitSessionId: '',
      unscopedStreamSessionIds: []
    }).drop
  ).toBe(true)
})
