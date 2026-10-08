import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { atom } from 'nanostores'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ save: vi.fn().mockResolvedValue({ ok: true }), scopes: [] as unknown[] }))

vi.mock('@/store/connections', () => ({ $activeConnectionId: atom('local') }))
vi.mock('@/store/profile', () => ({ $activeGatewayProfile: atom('default') }))
vi.mock('./profile-scope', () => ({ SettingsProfileScope: () => <span>Applies to</span> }))
vi.mock('@/hermes', async () => ({
  ...(await vi.importActual('@/hermes')),
  getGlobalModelOptions: vi
    .fn()
    .mockResolvedValue({ providers: [{ slug: 'local', name: 'Local', models: ['small'] }] }),
  getHermesConfigSchema: vi.fn().mockResolvedValue({ fields: {} }),
  saveHermesConfig: (...args: unknown[]) => api.save(...args)
}))
vi.mock('../hooks/use-config-record', () => ({
  useHermesConfigRecord: (scope: string) => {
    api.scopes.push(scope)

    return {
      data: { orchestration: { profiles: {}, routes: {}, mode: scope === 'research' ? 'observe' : 'auto' } },
      writeScope: scope
    }
  },
  hermesConfigCacheWriter: () => vi.fn()
}))

import { type OrchestrationRecord, profileInUse, validOrchestration } from './orchestration-data'
import { ProfileEditor } from './orchestration-editors'
import { RouteEditor } from './orchestration-graph-editor'
import { OrchestrationSettings } from './orchestration-settings'

beforeEach(() => {
  Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  api.scopes.length = 0
  Reflect.deleteProperty(Element.prototype, 'scrollIntoView')
})

describe('orchestration settings', () => {
  it('keeps existing profiles compact and retains edits when collapsed', async () => {
    function Profiles() {
      const [value, setValue] = useState<OrchestrationRecord>({
        profiles: { worker: { enabled: true, provider: 'local', model: 'small', level: 'fast' } },
        routes: {}
      })

      return <ProfileEditor dirty={false} onChange={setValue} onTest={vi.fn()} value={value} />
    }

    render(
      <QueryClientProvider client={new QueryClient()}>
        <Profiles />
      </QueryClientProvider>
    )
    const summary = screen.getByText('worker', { selector: 'summary span.font-medium' })
    expect(screen.getByLabelText('worker description').closest('details')?.open).toBe(false)
    fireEvent.click(summary)
    fireEvent.change(screen.getByLabelText('worker description'), { target: { value: 'Frontend work' } })
    expect(screen.getByLabelText('worker reasoning').closest('details')?.open).toBe(false)
    fireEvent.click(screen.getByText('Advanced settings'))
    expect(screen.getByRole('combobox', { name: 'worker reasoning' })).toBeTruthy()
    fireEvent.click(summary)
    expect(screen.getByLabelText('worker description').closest('details')?.open).toBe(false)
    fireEvent.click(summary)
    expect((screen.getByLabelText('worker description') as HTMLInputElement).value).toBe('Frontend work')
  })

  it('edits graph groups, supports undo, and rejects disconnected groups', () => {
    const changed = vi.fn()

    function Routes() {
      const [value, setValue] = useState<OrchestrationRecord>({
        profiles: {
          light: { enabled: true, provider: 'local', model: 'small', level: 'fast' },
          strong: { enabled: true, provider: 'local', model: 'large', level: 'deep' }
        },
        routes: { general: ['light', 'strong'] }
      })

      return (
        <RouteEditor
          onChange={next => {
            changed(next)
            setValue(next)
          }}
          value={value}
        />
      )
    }

    render(<Routes />)
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Frontend' } })
    expect(changed.mock.lastCall![0].graphs.general.nodes[0].label).toBe('Frontend')
    fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
    expect(screen.getByRole('alert').textContent).toContain('Connect every group')
    fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    expect(screen.queryByRole('alert')).toBeNull()
    expect(changed.mock.lastCall![0].graphs.general.nodes).toHaveLength(2)
  })

  it('selects an existing provider/model, saves a route, and protects its profile', async () => {
    const client = new QueryClient()

    const view = (subpage: string) => (
      <QueryClientProvider client={client}>
        <OrchestrationSettings scopeProfile="default" subpage={subpage} />
      </QueryClientProvider>
    )

    const rendered = render(view('profiles'))
    fireEvent.click(await screen.findByText('Add execution profile'))
    fireEvent.keyDown(screen.getByLabelText('profile_1 provider'), { key: 'Enter' })
    fireEvent.click(await screen.findByRole('option', { name: 'local' }))
    fireEvent.keyDown(screen.getByLabelText('profile_1 model'), { key: 'Enter' })
    fireEvent.click(await screen.findByRole('option', { name: 'small' }))
    rendered.rerender(view('routes'))
    fireEvent.click(await screen.findByText('Add workflow'))
    fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.save).toHaveBeenCalledWith(
        {
          orchestration: expect.objectContaining({
            profiles: { profile_1: expect.objectContaining({ provider: 'local', model: 'small' }) },
            routes: { general: ['profile_1'] }
          })
        },
        'default'
      )
    )
    rendered.rerender(view('profiles'))
    fireEvent.click(await screen.findByText('profile_1', { selector: 'summary span.font-medium' }))
    expect(
      (await screen.findByText('This profile is used by a route or verifier. Remove those references first.'))
        .textContent
    ).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Remove' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('keeps profile drafts isolated when switching scope', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    const view = (scope: string) => (
      <QueryClientProvider client={client}>
        <OrchestrationSettings scopeProfile={scope} subpage="profiles" />
      </QueryClientProvider>
    )

    const rendered = render(view('default'))
    fireEvent.click(await screen.findByText('Add execution profile'))
    expect(screen.getByLabelText('profile_1 id')).toBeTruthy()
    rendered.rerender(view('research'))
    await waitFor(() => expect(screen.queryByLabelText('profile_1 id')).toBeNull())
    expect(api.scopes).toContain('research')
    expect(api.save).not.toHaveBeenCalled()
  })

  it('does not save an incomplete execution profile', async () => {
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <OrchestrationSettings scopeProfile="default" subpage="profiles" />
      </QueryClientProvider>
    )
    fireEvent.click(await screen.findByText('Add execution profile'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Complete every profile')
    expect(api.save).not.toHaveBeenCalled()
  })

  it('rejects dangling and duplicate routes and protects a referenced profile', () => {
    const profiles = {
      fast: { enabled: true, provider: 'local', model: 'small', level: 'fast' },
      deep: { enabled: true, provider: 'local', model: 'large', level: 'deep' }
    }

    expect(validOrchestration({ profiles, routes: { coding: ['fast', 'deep'] } })).toBe(true)

    for (const route of [['missing'], ['fast', 'fast']]) {
      expect(validOrchestration({ profiles, routes: { coding: route } })).toBe(false)
    }

    expect(validOrchestration({ profiles, routes: { coding: ['deep', 'fast'] } })).toBe(true)
    expect(profileInUse({ profiles, routes: { coding: ['fast'] } }, 'fast')).toBe(true)
    expect(profileInUse({ profiles, routes: {}, verification: { verifier_profile: 'deep' } }, 'deep')).toBe(true)
  })
})
