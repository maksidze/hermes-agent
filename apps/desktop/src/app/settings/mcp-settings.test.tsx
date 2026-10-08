import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { McpServersController } from '../capabilities/mcp/use-mcp-servers'

import { McpSettings } from './mcp-settings'

const mocks = vi.hoisted(() => ({
  addServerEntry: vi.fn(),
  authenticate: vi.fn(),
  install: vi.fn(),
  setServerEnabled: vi.fn(),
  useMcpServers: vi.fn()
}))

vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      connectorsPage: { add: { action: 'Add server' } },
      settings: { mcp: { catalogInstallFailed: (name: string) => `Failed to install ${name}` }, nav: { mcp: 'MCP' } }
    }
  })
}))

vi.mock('../capabilities/mcp/use-mcp-servers', () => ({
  useMcpServers: mocks.useMcpServers
}))

vi.mock('../capabilities/mcp/install-catalog-entry', () => ({
  installBundledEntry: mocks.install
}))

vi.mock('../capabilities/connectors/connectors-directory', () => ({
  ConnectorsDirectory: ({ addYourOwn, cards, onServerToggle, onVerb, title }: any) => (
    <section>
      <h1>{title}</h1>
      {addYourOwn}
      {cards.map((card: any) => (
        <div key={card.slug}>
          <span>{card.name}</span>
          <button onClick={() => onServerToggle(card, false)} type="button">
            Disable {card.name}
          </button>
          {card.verb ? (
            <button onClick={() => onVerb(card)} type="button">
              {card.verb} {card.name}
            </button>
          ) : null}
        </div>
      ))}
    </section>
  )
}))

vi.mock('../capabilities/connectors/add-dialog', () => ({
  AddServerDialog: ({ open, profile }: any) => (open ? <p>Add dialog for {String(profile)}</p> : null)
}))

vi.mock('../capabilities/connectors/local-dialog', () => ({ LocalConnectorDialog: () => null }))
vi.mock('../capabilities/connectors/local-slots', () => ({ RemoveServerConfirm: () => null }))
vi.mock('../capabilities/connectors/use-open-connector-from-route', () => ({
  useOpenConnectorFromRoute: () => undefined
}))
vi.mock('./profile-scope', () => ({ SettingsProfileScope: () => <p>Applies to</p> }))

const catalogEntry = {
  args: [],
  auth_type: 'none',
  bootstrap: [],
  command: null,
  default_enabled: null,
  description: 'A catalog server',
  enabled: false,
  install_ref: null,
  install_url: null,
  installed: false,
  name: 'catalog-server',
  needs_install: false,
  post_install: '',
  required_env: [],
  source: 'bundled',
  transport: 'http',
  url: 'https://mcp.example.test'
}

function controller(): McpServersController {
  return {
    activeBlock: null,
    addServer: vi.fn(),
    addServerEntry: mocks.addServerEntry,
    authenticate: mocks.authenticate,
    authing: null,
    availableCatalog: [catalogEntry],
    blocks: [],
    catalog: [catalogEntry],
    catalogLoading: false,
    config: { mcp_servers: { filesystem: { command: 'npx' } } },
    configError: null,
    configFailed: false,
    configLoading: false,
    costFor: () => ({ tokens: null, uses: null }),
    cursor: 0,
    descriptionFor: () => null,
    dirty: false,
    docVersion: 0,
    draft: '{}',
    editorApi: { current: null },
    focusServer: vi.fn(),
    importServers: vi.fn(),
    names: ['filesystem'],
    onCatalogInstalled: vi.fn(async () => undefined),
    patchDraft: vi.fn(),
    probes: {},
    profilePending: false,
    refetchConfig: vi.fn(),
    removeServer: vi.fn(async () => true),
    reset: vi.fn(),
    resetDraft: vi.fn(),
    runProbe: vi.fn(async () => undefined),
    saveDoc: vi.fn(async () => undefined),
    saving: false,
    selected: null,
    servers: { filesystem: { command: 'npx' } },
    setCursor: vi.fn(),
    setDraft: vi.fn(),
    setServerEnabled: mocks.setServerEnabled,
    setServerTools: vi.fn(async () => true),
    statuses: { filesystem: 'unknown' },
    toggleTool: vi.fn(async () => undefined),
    toolCounts: {},
    usageByServer: {}
  }
}

describe('Settings MCP management', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows configured and catalog servers and keeps writes in the selected profile', () => {
    mocks.useMcpServers.mockReturnValue(controller())

    render(<McpSettings profile="research" />)

    expect(screen.getByRole('heading', { name: 'MCP' })).toBeTruthy()
    expect(screen.getByText('Filesystem')).toBeTruthy()
    expect(screen.getByText('Catalog Server')).toBeTruthy()
    expect(mocks.useMcpServers).toHaveBeenCalledWith({ gateway: null, profile: 'research' })

    fireEvent.click(screen.getByRole('button', { name: 'Disable Filesystem' }))
    expect(mocks.setServerEnabled).toHaveBeenCalledWith('filesystem', false)

    fireEvent.click(screen.getByRole('button', { name: 'Add server' }))
    expect(screen.getByText('Add dialog for research')).toBeTruthy()
  })

  it('installs a catalog server immediately when it needs no credentials', () => {
    const value = controller()
    mocks.useMcpServers.mockReturnValue(value)

    render(<McpSettings profile="default" />)
    fireEvent.click(screen.getByRole('button', { name: 'install Catalog Server' }))

    expect(mocks.install).toHaveBeenCalledWith(catalogEntry, {}, 'default')
  })
})
