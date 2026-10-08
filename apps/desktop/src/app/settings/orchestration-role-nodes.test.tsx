import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { OrchestrationRecord } from './orchestration-data'
import { RouteEditor } from './orchestration-graph-editor'

beforeEach(() => Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() }))
afterEach(() => { cleanup(); Reflect.deleteProperty(Element.prototype, 'scrollIntoView') })

it('edits shared roles and adaptive entry without adding workers', async () => {
  const changed = vi.fn()

  function Editor() {
    const [value, setValue] = useState<OrchestrationRecord>({
      profiles: {
        worker: { enabled: true, provider: 'local', model: 'small', level: 'fast' },
        architect: { enabled: true, provider: 'local', model: 'large', level: 'deep' }
      },
      routes: { general: ['worker', 'architect'] }
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

  render(<Editor />)
  expect(screen.getByText('Planning')).toBeTruthy()
  fireEvent.keyDown(screen.getByLabelText('Architect model'), { key: 'Enter' })
  fireEvent.click(await screen.findByRole('option', { name: 'large · architect' }))
  expect(changed.mock.lastCall![0].automation.planner_profile).toBe('architect')
  fireEvent.keyDown(screen.getByRole('combobox', { name: 'Reviewer model' }), { key: 'Enter' })
  fireEvent.click(await screen.findByRole('option', { name: 'large · architect' }))
  expect(changed.mock.lastCall![0].verification.verifier_profile).toBe('architect')
  fireEvent.click(screen.getByLabelText('Architect chooses the starting group'))
  expect(changed.mock.lastCall![0].routing.adaptive_entry).toBe(false)
  expect(changed.mock.lastCall![0].routes).toEqual({ general: ['worker', 'architect'] })
  expect(changed.mock.lastCall![0].graphs).toBeUndefined()
  expect(screen.getAllByText('Reviewer model: large')).toHaveLength(2)
})

it('adds a node for the chosen model without silently connecting it to the architect', async () => {
  const changed = vi.fn()

  const value: OrchestrationRecord = {
    profiles: {
      luna: { enabled: true, provider: 'local', model: 'Luna', level: 'balanced' },
      sol: { enabled: true, provider: 'local', model: 'Sol', level: 'deep' }
    },
    routes: { modeling_3d: ['luna'] }
  }

  render(<RouteEditor onChange={changed} value={value} />)
  fireEvent.keyDown(screen.getByRole('combobox', { name: 'Add model' }), { key: 'Enter' })
  fireEvent.click(await screen.findByRole('option', { name: 'Sol' }))
  fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
  const graph = changed.mock.lastCall![0].graphs.modeling_3d
  expect(graph.nodes.at(-1).profiles).toEqual(['sol'])
  expect(graph.nodes.at(-1).label).toBe('Sol')
  expect(graph.entry_nodes).toEqual(['step_0'])
})
