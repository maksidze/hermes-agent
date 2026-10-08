import { mediaTagValues } from '@/lib/chat-messages/parts'
import { isFileMediaPath, mediaKind } from '@/lib/media'

/** MCP content blocks and cached MEDIA receipts share the normal media bridge. */
export function toolResultImages(value: unknown, depth = 0): string[] {
  if (depth > 8) {return []}

  const valid = (url: unknown): url is string =>
    typeof url === 'string' &&
    (/^data:image\/(png|jpeg|webp|gif);base64,/i.test(url) ||
      (/^https?:\/\//i.test(url) && mediaKind(url.split(/[?#]/)[0]) === 'image') ||
      (isFileMediaPath(url) && mediaKind(url) === 'image'))

  const walk = (item: unknown) => toolResultImages(item, depth + 1)

  if (typeof value === 'string') {
    const text = value.replace(/^<untrusted_tool_result[^>]*>[\s\S]*?\n\n/, '').replace(/\n<\/untrusted_tool_result>\s*$/, '')

    try {
      return walk(JSON.parse(text))
    } catch {
      return [...new Set(mediaTagValues(text).map(path => path.replace(/^["']|["']$/g, '')).filter(valid))]
    }
  }

  if (Array.isArray(value)) {return [...new Set(value.flatMap(walk))]}

  if (!value || typeof value !== 'object') {return []}
  const row = value as Record<string, unknown>
  const urls = [row.image_url, row.url, row.image_path]

  if (row.type === 'image' && typeof row.data === 'string') {urls.push(`data:${row.mimeType};base64,${row.data}`)}

  if (row.image_url && typeof row.image_url === 'object') {urls.push((row.image_url as Record<string, unknown>).url)}

  return [...new Set([...urls.filter(valid), ...['result', 'content', 'text', 'structuredContent'].flatMap(key => walk(row[key]))])]
}
