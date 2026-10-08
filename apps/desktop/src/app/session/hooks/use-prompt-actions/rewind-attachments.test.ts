import { describe, expect, it, vi } from 'vitest'

import { reconcileResumeMessages } from '@/app/session/hooks/use-session-actions/utils'
import { type ChatMessage, textPart } from '@/lib/chat-messages'
import { toChatMessages } from '@/lib/chat-messages/hydration'

import { planEdit, planReload, planRestore, runRewindSubmit } from './rewind'

const refs = [
  '@image:"D:/project/machine photo.png"',
  '@file:D:/project/spec.pdf',
  '@file:D:/project/clip.mp4',
  '@file:D:/project/voice.wav'
]

const user: ChatMessage = {
  id: 'user-1',
  role: 'user',
  rowId: 7,
  parts: [textPart('Model this machine')],
  attachmentRefs: ['blob:preview'],
  attachmentSourceRefs: refs
}

describe('replaying attachment-bearing turns', () => {
  it('sends original image, document, video and audio refs through the truncating RPC', async () => {
    const request = vi.fn().mockResolvedValue({})
    const plan = planReload([user], null)!
    await runRewindSubmit(
      request,
      'session',
      plan.text,
      plan.truncateOrdinal,
      plan.truncateMessageId,
      false,
      undefined,
      plan.truncateRowId,
      plan.sourceText
    )
    expect(request).toHaveBeenCalledWith(
      'prompt.submit',
      expect.objectContaining({
        text: refs.join('\n') + '\n\nModel this machine',
        truncate_before_row_id: 7
      }),
      expect.any(Number)
    )
    expect(planRestore([user], user.id).text).toBe(plan.text)

    const edited = planEdit([user], {
      role: 'user',
      sourceId: user.id,
      parentId: null,
      runConfig: undefined,
      createdAt: new Date(),
      metadata: { custom: {} },
      content: [{ type: 'text', text: 'Make it detailed' }],
      attachments: []
    } as Parameters<typeof planEdit>[1])!

    expect(edited.text).toBe(refs.join('\n') + '\n\nMake it detailed')
    expect(edited.sourceText).toBe(plan.sourceText)
  })

  it('can replay an attachment-only turn without inventing a text caption', () => {
    expect(planReload([{ ...user, parts: [] }], null)?.text).toBe(refs.join('\n'))
  })

  it('rehydrates durable refs without duplicating them on restore', () => {
    const text = '@file:/project/spec.pdf\n\nModel this machine\n@image:/project/ref.png'
    const messages = toChatMessages([{ role: 'user', content: text, id: 7 }])
    const plan = planReload(messages, null)!
    expect(plan.text.match(/@image:/g)).toHaveLength(1)
    expect(plan.text.match(/@file:/g)).toHaveLength(1)
    expect(plan.text).toContain('Model this machine')
  })

  it('retains upload refs across a text-only resume without borrowing refs from a different turn', () => {
    const textOnly = { ...user, attachmentRefs: undefined, attachmentSourceRefs: undefined }
    const resumed = reconcileResumeMessages([textOnly], [user])
    expect(planReload(resumed, null)?.text).toContain(refs[0])
    const changed = reconcileResumeMessages([{ ...textOnly, parts: [textPart('Different request')] }], [user])
    expect(changed[0].attachmentSourceRefs).toBeUndefined()
  })
})
