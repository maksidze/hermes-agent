import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, it, vi } from 'vitest'

import { type OrchestrationRecord, profileInUse, validOrchestration } from './orchestration-data'
import { RouteEditor } from './orchestration-graph-editor'
import { SpecializationEditor } from './orchestration-specializations'

afterEach(cleanup)

const initial: OrchestrationRecord = {
  profiles: {
    fast: { enabled: true, provider: 'local', model: 'small', level: 'fast' },
    reviewer: { enabled: true, provider: 'local', model: 'reviewer', level: 'fast' }
  },
  routes: { general: ['fast'] }
}

it('creates editable disabled categories while preserving existing model choices', () => {
  const changed = vi.fn()

  function Editor() {
    const [value, setValue] = useState(initial)

    return (
      <SpecializationEditor
        onChange={next => {
          setValue(next)
          changed(next)
        }}
        value={value}
      />
    )
  }

  render(<Editor />)
  fireEvent.click(screen.getByRole('button', { name: 'Add four category templates' }))
  let saved = changed.mock.lastCall![0] as OrchestrationRecord
  expect(Object.values(saved.specializations!).every(c => !c.enabled)).toBe(true)
  expect(saved.specializations!.local_private.local_only).toBe(true)
  expect(saved.specializations!.roleplay.isolate_workspace).toBe(false)
  expect(saved.profiles).toBe(initial.profiles)
  fireEvent.change(screen.getByLabelText('roleplay description'), { target: { value: 'Distinct character voices' } })
  fireEvent.click(screen.getByRole('switch', { name: 'roleplay' }))
  fireEvent.click(screen.getByRole('button', { name: 'Add four category templates' }))
  saved = changed.mock.lastCall![0] as OrchestrationRecord
  expect(saved.specializations!.roleplay.description).toBe('Distinct character voices')
  expect(saved.specializations!.roleplay.enabled).toBe(true)
  expect(validOrchestration(saved)).toBe(true)
})

it('updates category references on route rename and protects referenced roles and routes', () => {
  const changed = vi.fn()

  const value: OrchestrationRecord = {
    ...initial,
    specializations: {
      roleplay: {
        enabled: true,
        description: 'Character voices',
        route: 'general',
        local_only: false,
        verifier_profile: 'reviewer'
      }
    }
  }

  render(<RouteEditor onChange={changed} value={value} />)
  expect((screen.getAllByRole('button', { name: 'Remove' })[0] as HTMLButtonElement).disabled).toBe(true)
  fireEvent.blur(screen.getByLabelText('general id'), { target: { value: 'dialogue' } })
  const renamed = changed.mock.lastCall![0] as OrchestrationRecord
  expect(renamed.specializations!.roleplay.route).toBe('dialogue')
  expect(validOrchestration(renamed)).toBe(true)
  expect(profileInUse(renamed, 'reviewer')).toBe(true)
  expect(validOrchestration({ ...renamed, profiles: { fast: initial.profiles.fast } })).toBe(false)
  expect(validOrchestration({ ...renamed, routes: {} })).toBe(false)
})
