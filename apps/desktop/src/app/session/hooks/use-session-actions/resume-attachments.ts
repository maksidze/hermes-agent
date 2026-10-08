import type { ChatMessage } from '@/lib/chat-messages'

/** Text-only inflight snapshots omit refs; only the same user turn may inherit them. */
export function preserveAttachmentRefs(message: ChatMessage, previous: ChatMessage, sameText: boolean): ChatMessage {
  if (!sameText || message.role !== 'user') {
    return message
  }

  return (['attachmentRefs', 'attachmentSourceRefs'] as const).reduce((current, key) => {
    const refs = previous[key]

    return current[key] === undefined && refs?.length ? { ...current, [key]: [...refs] } : current
  }, message)
}
