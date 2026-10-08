import { getViewportForBounds, useNodesInitialized, useReactFlow } from '@xyflow/react'
import { type RefObject, useEffect } from 'react'

interface Bounds { x: number; y: number; width: number; height: number }

export function measuredViewport(bounds: Bounds, width: number, height: number) {
  if (![bounds.x, bounds.y, bounds.width, bounds.height, width, height].every(Number.isFinite) ||
      Math.min(bounds.width, bounds.height, width, height) <= 0) {return null}

  const viewport = getViewportForBounds(bounds, width, height, 0.2, 2, 0.2)

  return Object.values(viewport).every(Number.isFinite) ? viewport : null
}

/** Fit only measured nodes; queuing fitView while nodes are replaced can feed
 * invalid geometry back into the controlled-node update loop. */
export function MeasuredViewport({ count, container }: { count: number; container: RefObject<HTMLDivElement | null> }) {
  const initialized = useNodesInitialized()
  const { getNodes, getNodesBounds, setViewport } = useReactFlow()
  useEffect(() => {
    if (!initialized) {return}
    const nodes = getNodes()
    const element = container.current

    if (!element) {return}
    const viewport = measuredViewport(getNodesBounds(nodes), element.clientWidth, element.clientHeight)

    if (viewport) {void setViewport(viewport)}
  }, [count, initialized, getNodes, getNodesBounds, setViewport, container])

  return null
}
