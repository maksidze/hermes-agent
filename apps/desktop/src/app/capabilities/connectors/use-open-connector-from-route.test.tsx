import { render, screen, waitFor } from '@testing-library/react'
import { useCallback, useState } from 'react'
import { MemoryRouter, useLocation } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import type { ConnectorCardModel } from './types'
import { useOpenConnectorFromRoute } from './use-open-connector-from-route'

const mocks = vi.hoisted(() => ({ openToolsList: vi.fn() }))

vi.mock('./tools-summary', () => ({ openToolsList: mocks.openToolsList }))

const filesystem = {
  inCatalog: false,
  name: 'Filesystem',
  residency: 'local',
  slug: 'filesystem',
  state: 'connected',
  stateWord: 'serverOn',
  ways: {
    hosted: null,
    local: { installed: true, serverName: 'filesystem', state: 'connected' }
  }
} as ConnectorCardModel

function Harness() {
  const [opened, setOpened] = useState('')
  const open = useCallback((key: string) => setOpened(key), [])
  const location = useLocation()

  useOpenConnectorFromRoute([filesystem], open)

  return <p>{`${opened}|${location.search}`}</p>
}

describe('connector route targeting', () => {
  it('opens the requested MCP server and consumes only its targeting params', async () => {
    render(
      <MemoryRouter initialEntries={['/settings?tab=mcp&server=filesystem&tool=read_file']}>
        <Harness />
      </MemoryRouter>
    )

    await waitFor(() => expect(screen.getByText('local:filesystem|?tab=mcp')).toBeTruthy())
    expect(mocks.openToolsList).toHaveBeenCalledWith('filesystem')
  })
})
