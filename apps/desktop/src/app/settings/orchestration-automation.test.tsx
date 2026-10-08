import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { AutomationSetup, recommendedSetup } from './orchestration-automation'
import { profileInUse, validOrchestration } from './orchestration-data'

afterEach(cleanup)

const configuration = {
  profiles: Object.fromEntries(
    ['fast', 'balanced', 'deep'].map(level => [
      level,
      {
        enabled: true,
        provider: 'local',
        model: `model-${level}`,
        level
      }
    ])
  ),
  routes: { general: ['fast', 'balanced', 'deep'] }
}

it('sets up an existing team in one action without changing profiles or routes', () => {
  const change = vi.fn()
  render(<AutomationSetup onChange={change} value={configuration} />)
  fireEvent.click(screen.getByRole('button', { name: 'Use recommended setup' }))
  const value = change.mock.calls[0][0]
  expect(value.profiles).toBe(configuration.profiles)
  expect(value.routes).toBe(configuration.routes)
  expect(value.automation).toEqual({ mode: 'all', planner_profile: 'deep', max_tasks: 6 })
  expect(value.verification.verifier_profile).toBe('balanced')
  expect(value.workspace).toEqual({ enabled: true, apply_on_success: true })
  expect(value.budget.max_attempts).toBeGreaterThan(value.automation.max_tasks)
  expect(validOrchestration(value)).toBe(true)
})

it('protects architect and fixed worker references and allows the route to supply a default architect', () => {
  const value = { ...recommendedSetup(configuration), routes: {} }
  expect(profileInUse(value, 'deep')).toBe(true)
  expect(profileInUse({ ...value, routing: { preferred_profile: 'fast' } }, 'fast')).toBe(true)
  expect(validOrchestration({ ...configuration, enabled: true })).toBe(true)
})
