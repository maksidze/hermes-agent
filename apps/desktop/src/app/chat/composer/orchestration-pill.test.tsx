import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ read: vi.fn(), save: vi.fn(), owner: { connectionId: 'remote', profile: 'writer' } }))
vi.mock('@/store/connections', () => ({ $activeConnectionId: atom('local') }))
vi.mock('@/store/profile', () => ({ $activeGatewayProfile: atom('default') }))
vi.mock('./scope', () => ({ useComposerScope: () => api.owner }))
vi.mock('@/hermes', async () => ({
  ...(await vi.importActual('@/hermes')),
  getHermesConfigRecord: (...args: unknown[]) => api.read(...args),
  saveHermesConfig: (...args: unknown[]) => api.save(...args)
}))

import { queryClient } from '@/lib/query-client'

import { orchestrationPatch } from './orchestration-options'
import { OrchestrationPill } from './orchestration-pill'

const config = {
  enabled: false,
  profiles: {
    fast: { enabled: true, provider: 'local', model: 'small', level: 'fast' },
    deep: { enabled: true, provider: 'local', model: 'large', level: 'deep' }
  },
  routes: { general: ['fast', 'deep'] }
}

function view() {
  return (
    <QueryClientProvider client={queryClient}>
      <OrchestrationPill disabled={false}>
        <button>Model selector</button>
        <button>Reasoning selector</button>
      </OrchestrationPill>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  api.owner = { connectionId: 'remote', profile: 'writer' }
  api.read.mockResolvedValue({ orchestration: config })
  api.save.mockResolvedValue({ ok: true })
  Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
})
afterEach(() => {
  cleanup()
  queryClient.clear()
  vi.resetAllMocks()
  Reflect.deleteProperty(Element.prototype, 'scrollIntoView')
})

it('shows controls for a configured profile and writes the composer owner, not the active profile', async () => {
  render(view())
  const toggle = await screen.findByRole('switch', { name: 'Orchestration' })
  expect(toggle.getAttribute('aria-checked')).toBe('false')
  expect(screen.getByText('Model selector')).toBeTruthy()
  expect(screen.getByText('Reasoning selector')).toBeTruthy()
  fireEvent.click(toggle)
  await waitFor(() =>
    expect(api.save).toHaveBeenCalledWith(
      { orchestration: expect.objectContaining({ enabled: true }) },
      { connectionId: 'remote', profile: 'writer' }
    )
  )
  expect(api.read).toHaveBeenCalledWith({ connectionId: 'remote', profile: 'writer' })
  await waitFor(() => expect(toggle.getAttribute('aria-checked')).toBe('true'))
  expect(screen.queryByText('Model selector')).toBeNull()
  expect(screen.queryByText('Reasoning selector')).toBeNull()
  fireEvent.click(toggle)
  await waitFor(() => expect(toggle.getAttribute('aria-checked')).toBe('false'))
  expect(screen.getByText('Model selector')).toBeTruthy()
  expect(screen.getByText('Reasoning selector')).toBeTruthy()
})

it('rolls back a failed switch and keeps an error visible', async () => {
  api.save.mockRejectedValueOnce(new Error('Write failed'))
  render(view())
  fireEvent.click(await screen.findByRole('switch', { name: 'Orchestration' }))
  expect((await screen.findByRole('alert')).textContent).toContain('Write failed')
  expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('false')
})

it('keeps a late failed save in its original profile after switching composer owners', async () => {
  let rejectSave!: (reason: Error) => void
  api.save.mockImplementationOnce(
    () =>
      new Promise((_resolve, reject) => {
        rejectSave = reject
      })
  )
  const rendered = render(view())
  fireEvent.click(await screen.findByRole('switch', { name: 'Orchestration' }))
  await waitFor(() => expect(api.save).toHaveBeenCalled())
  api.owner = { connectionId: 'remote', profile: 'another' }
  rendered.rerender(view())
  await waitFor(() => expect(api.read).toHaveBeenCalledWith({ connectionId: 'remote', profile: 'another' }))
  await act(async () => rejectSave(new Error('Old profile write failed')))
  expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('false')
  expect(screen.queryByRole('alert')).toBeNull()
})

it('does not offer orchestration before any execution profile exists', async () => {
  api.read.mockResolvedValue({ orchestration: { profiles: {}, routes: {} } })
  render(view())
  await waitFor(() => expect(api.read).toHaveBeenCalled())
  expect(screen.queryByRole('switch')).toBeNull()
})

it('makes a usable team from a single profile without requiring setup elsewhere', () => {
  expect(orchestrationPatch({ profiles: { fast: config.profiles.fast }, routes: {} }, true)).toEqual({
    enabled: true,
    routes: { general: ['fast'] },
    routing: { default_route: 'general' },
    automation: { planner_profile: 'fast' },
    verification: { verifier_profile: 'fast' }
  })
  expect(orchestrationPatch(config, false)).toEqual({ enabled: false })
})

it('selects a different architect while keeping the execution route', async () => {
  render(view())
  fireEvent.keyDown(await screen.findByRole('button', { name: 'Orchestration team and profile' }), { key: 'Enter' })
  fireEvent.click(await screen.findByRole('menuitemradio', { name: 'deep · large' }))
  await waitFor(() =>
    expect(api.save).toHaveBeenCalledWith(
      { orchestration: { automation: { planner_profile: 'deep' } } },
      { connectionId: 'remote', profile: 'writer' }
    )
  )
})
