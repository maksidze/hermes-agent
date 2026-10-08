import { useState } from 'react'

import { MarkdownImage } from '@/components/assistant-ui/markdown-text'
import { DisclosureRow } from '@/components/chat/disclosure-row'
import { useI18n } from '@/i18n'
import { toolResultImages } from '@/lib/tool-result-images'

interface OutputProps {
  part: { toolName: string; result?: unknown }
  imageUrl?: string
}

export function hasOutputImages({ part, imageUrl }: OutputProps) {
  return Boolean(imageUrl || (part.toolName.startsWith('mcp__') && toolResultImages(part.result).length))
}

export function ToolOutputImages({ part, imageUrl }: OutputProps) {
  const { t } = useI18n()

  if (part.toolName.startsWith('mcp__')) {return <ToolResultImages images={toolResultImages(part.result)} />}

  if (!imageUrl) {return null}

  return <div className="max-w-72 overflow-hidden rounded-[0.25rem] border border-(--ui-stroke-tertiary)">
    <MarkdownImage alt={t.assistant.tool.outputAlt} src={imageUrl} />
  </div>
}

export function ProgressImage({ event, fields }: { event: string; fields?: Record<string, string> }) {
  if (event !== 'tool_image' || !fields?.image_path) {return null}

  return <ToolResultImages images={[fields.image_path]} />
}

export function ToolResultImages({ images }: { images: string[] }) {
  const [open, setOpen] = useState(false)
  const { t } = useI18n()

  if (!images.length) {return null}
  const label = t.assistant.tool.outputAlt

  return (
    <div className="grid min-w-0 gap-2">
      <DisclosureRow onToggle={() => setOpen(!open)} open={open}>{label} · {images.length}</DisclosureRow>
      {open && images.map(src => <MarkdownImage alt={label} key={src} src={src} />)}
    </div>
  )
}
