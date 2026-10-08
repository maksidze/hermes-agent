import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import type { HermesGateway, ProfileScope } from '@/hermes'
import { useI18n } from '@/i18n'
import { notifyError } from '@/store/notifications'

import { AddServerDialog } from '../capabilities/connectors/add-dialog'
import { ConnectorsDirectory } from '../capabilities/connectors/connectors-directory'
import { joinBundledEntries, joinLocalServers } from '../capabilities/connectors/data/join'
import { cardKey, deriveCards, EMPTY_CONNECTORS_FILTER, localServerName } from '../capabilities/connectors/derive'
import { LocalConnectorDialog } from '../capabilities/connectors/local-dialog'
import { RemoveServerConfirm } from '../capabilities/connectors/local-slots'
import type { ConnectorCardModel, ConnectorsFilter } from '../capabilities/connectors/types'
import { useOpenConnectorFromRoute } from '../capabilities/connectors/use-open-connector-from-route'
import { installBundledEntry } from '../capabilities/mcp/install-catalog-entry'
import { useMcpServers } from '../capabilities/mcp/use-mcp-servers'

import { SettingsProfileScope } from './profile-scope'

export interface McpSettingsProps {
  gateway?: HermesGateway | null
  profile: ProfileScope
}

/** Settings owns the management view; Capabilities remains the broader
 * discovery surface for hosted connectors and plugin-provided servers. */
export function McpSettings({ gateway = null, profile }: McpSettingsProps) {
  const { t } = useI18n()
  const controller = useMcpServers({ gateway, profile })
  const [filter, setFilter] = useState<ConnectorsFilter>(EMPTY_CONNECTORS_FILTER)
  const [openKey, setOpenKey] = useState<null | string>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [removeServer, setRemoveServer] = useState<null | ConnectorCardModel>(null)
  const [installing, setInstalling] = useState<null | string>(null)

  const local = useMemo(
    () =>
      joinLocalServers({
        catalog: controller.catalog,
        servers: controller.servers,
        status: controller.statuses,
        toolCounts: controller.toolCounts,
        usage: controller.usageByServer
      }),
    [controller.catalog, controller.servers, controller.statuses, controller.toolCounts, controller.usageByServer]
  )

  const bundled = useMemo(() => joinBundledEntries(controller.availableCatalog), [controller.availableCatalog])
  const cards = useMemo(() => deriveCards({ bundled, hosted: [], local }), [bundled, local])
  const openCard = useMemo(() => cards.find(card => cardKey(card) === openKey) ?? null, [cards, openKey])

  useOpenConnectorFromRoute(cards, setOpenKey)

  const bundledEntry = (card: ConnectorCardModel) =>
    controller.availableCatalog.find(candidate => candidate.name === card.ways.local?.entryName) ?? null

  const install = async (card: ConnectorCardModel, env: Record<string, string>) => {
    const entry = bundledEntry(card)

    if (!entry) {
      return
    }

    setInstalling(cardKey(card))

    try {
      await installBundledEntry(entry, env, profile)
      await controller.onCatalogInstalled()
      setOpenKey(cardKey(card))
    } catch (error) {
      notifyError(error, t.settings.mcp.catalogInstallFailed(card.name))
    } finally {
      setInstalling(null)
    }
  }

  const runVerb = (card: ConnectorCardModel) => {
    if (card.verb === 'authenticate') {
      void controller.authenticate(localServerName(card))

      return
    }

    const entry = bundledEntry(card)

    if (card.verb === 'install' && entry && !entry.required_env.some(field => field.required)) {
      void install(card, {})

      return
    }

    setOpenKey(cardKey(card))
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 px-4 pb-2">
      <SettingsProfileScope />
      <ConnectorsDirectory
        addYourOwn={
          <Button disabled={controller.profilePending} onClick={() => setAddOpen(true)} size="xs" variant="outline">
            {t.connectorsPage.add.action}
          </Button>
        }
        busyKey={installing}
        cards={cards}
        filter={filter}
        loading={(controller.configLoading || controller.catalogLoading) && cards.length === 0}
        onFilterChange={setFilter}
        onOpen={card => setOpenKey(cardKey(card))}
        onServerToggle={(card, next) => void controller.setServerEnabled(localServerName(card), next)}
        onVerb={runVerb}
        selectedKey={openKey}
        title={t.settings.nav.mcp}
      />

      {openCard ? (
        <LocalConnectorDialog
          card={openCard}
          controller={controller}
          installFields={bundledEntry(openCard)?.required_env}
          installing={installing === cardKey(openCard)}
          onClose={() => setOpenKey(null)}
          onConnect={() => undefined}
          onInstall={env => void install(openCard, env)}
          onReconnect={() => undefined}
          onRemoveServer={() => setRemoveServer(openCard)}
          profile={profile}
        />
      ) : null}

      <AddServerDialog controller={controller} onOpenChange={setAddOpen} open={addOpen} profile={profile} />

      <RemoveServerConfirm
        card={removeServer}
        controller={controller}
        onClose={() => setRemoveServer(null)}
        onRemoved={() => setOpenKey(null)}
      />
    </div>
  )
}
