/** Copilot message list -- scrollable list of messages. */

import { useEffect, useRef } from 'react'
import type { CopilotMessage, CopilotRun } from '../../types/accountCopilot'
import CopilotMessageBubble from './CopilotMessageBubble'

interface Props {
  messages: CopilotMessage[]
  runs?: CopilotRun[]
  selectedRunId?: string
  onSelectRun?: (runId: string) => void
}

export default function CopilotMessageList({ messages, runs, selectedRunId, onSelectRun }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  if (messages.length === 0) {
    return (
      <div className="copilot-messages copilot-messages--empty">
        <p>Start a conversation with your Account Copilot.</p>
        <p>Ask about your portfolio, positions, trades, or risk.</p>
      </div>
    )
  }

  return (
    <div className="copilot-messages">
      {messages.map((msg) => {
        const run = runs?.find((r) => r.user_message_id === msg.id || r.assistant_message_id === msg.id)
        return (
          <CopilotMessageBubble
            key={msg.id}
            message={msg}
            run={run}
            selected={run?.id === selectedRunId}
            onSelectRun={onSelectRun}
          />
        )
      })}
      <div ref={endRef} />
    </div>
  )
}
