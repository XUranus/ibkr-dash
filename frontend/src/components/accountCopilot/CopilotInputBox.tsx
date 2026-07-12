/** Copilot input box -- text area with send button. */

import { useState, useRef, useCallback } from 'react'

interface Props {
  loading?: boolean
  onSend: (message: string) => void
}

export default function CopilotInputBox({ loading, onSend }: Props) {
  const [draft, setDraft] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const submit = useCallback(() => {
    if (loading || !draft.trim()) return
    onSend(draft.trim())
    setDraft('')
  }, [draft, loading, onSend])

  function handleKeydown(event: React.KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="copilot-input">
      <textarea
        ref={textareaRef}
        value={draft}
        rows={3}
        placeholder="Ask about your IBKR account, positions, trades, risk, or market events..."
        disabled={loading}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeydown}
        className="copilot-input__textarea"
      />
      <button
        className="copilot-input__button"
        onClick={submit}
        disabled={loading || !draft.trim()}
      >
        {loading ? 'Sending...' : 'Send'}
      </button>
    </div>
  )
}
