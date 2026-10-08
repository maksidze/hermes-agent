import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { ToolResultImages } from './result-images'

vi.mock('@/components/assistant-ui/markdown-text', () => ({ MarkdownImage: ({ src, alt }: { src: string; alt: string }) => <img alt={alt} src={src} /> }))
afterEach(cleanup)

it('keeps images unmounted until the user expands the disclosure', () => {
  const images = ['data:image/png;base64,YWJj', 'data:image/png;base64,ZGVm']
  render(<ToolResultImages images={images} />)
  expect(screen.queryAllByRole('img')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { expanded: false }))
  expect(screen.getAllByRole('img').map(img => img.getAttribute('src'))).toEqual(images)
  fireEvent.click(screen.getByRole('button', { expanded: true }))
  expect(screen.queryAllByRole('img')).toHaveLength(0)
})
