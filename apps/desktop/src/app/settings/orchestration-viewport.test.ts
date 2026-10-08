import { expect, it } from 'vitest'

import { measuredViewport } from './orchestration-viewport'

it('never fits unmeasured, hidden or non-finite geometry', () => {
  const bounds = { x: -240, y: -200, width: 600, height: 1000 }
  expect(measuredViewport(bounds, 0, 520)).toBeNull()
  expect(measuredViewport({ ...bounds, width: 0 }, 1000, 520)).toBeNull()
  expect(measuredViewport({ ...bounds, x: NaN }, 1000, 520)).toBeNull()
  expect(measuredViewport({ ...bounds, height: Infinity }, 1000, 520)).toBeNull()
  const viewport = measuredViewport(bounds, 1000, 520)
  expect(viewport).not.toBeNull()
  expect(Object.values(viewport!).every(Number.isFinite)).toBe(true)
})
