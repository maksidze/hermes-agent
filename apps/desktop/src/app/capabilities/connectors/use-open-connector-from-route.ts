import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { cardKey, localServerName } from './derive'
import { openToolsList } from './tools-summary'
import type { ConnectorCardModel } from './types'

const toolsListKey = (card: ConnectorCardModel) => (card.residency === 'local' ? localServerName(card) : card.slug)

/** Consume a connector/server deep link only after its row has loaded. Shared
 * by Capabilities and Settings so both surfaces preserve row + tool targeting. */
export function useOpenConnectorFromRoute(cards: readonly ConnectorCardModel[], open: (key: string) => void): void {
  const { hash, pathname, search } = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(search)
    const server = params.get('server')
    const slug = params.get('connector')

    if (!server && !slug) {
      return
    }

    const target = server
      ? cards.find(card => card.residency === 'local' && card.slug === server)
      : cards.find(card => card.slug === slug)

    if (!target) {
      return
    }

    if (params.get('tool')) {
      openToolsList(toolsListKey(target))
    }

    open(cardKey(target))
    params.delete('server')
    params.delete('connector')
    params.delete('tool')

    const query = params.toString()
    navigate({ hash, pathname, search: query ? `?${query}` : '' }, { replace: true })
  }, [cards, hash, navigate, open, pathname, search])
}
