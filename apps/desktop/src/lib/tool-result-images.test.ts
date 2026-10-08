import { expect, it } from 'vitest'

import { toolResultImages } from './tool-result-images'

it('unwraps MCP receipts and preserves Windows paths with spaces', () => {
  const path = 'D:\\Project files\\preview.png'
  const result = `<untrusted_tool_result source="mcp__editor__preview">\nExternal data\n\n${JSON.stringify({ result: `MEDIA:${path}\nRendered` })}\n</untrusted_tool_result>`
  expect(toolResultImages(result)).toEqual([path])
})

it('collects native and nested images without interpreting unrelated URLs as images', () => {
  const image = 'data:image/png;base64,YWJj'
  expect(toolResultImages({ content: [
    { type: 'image', mimeType: 'image/png', data: 'YWJj' },
    { type: 'image_url', image_url: { url: image } },
    { type: 'text', text: 'MEDIA:/tmp/two.webp' },
    { url: 'javascript:alert(1)' },
  ] })).toEqual([image, '/tmp/two.webp'])
})
