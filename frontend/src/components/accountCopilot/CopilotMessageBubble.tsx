/** Copilot message bubble -- displays a single chat message. */

import type { CopilotMessage, CopilotRun } from '../../types/accountCopilot'

interface Props {
  message: CopilotMessage
  run?: CopilotRun
  selected?: boolean
  onSelectRun?: (runId: string) => void
}

function statusLabel(status?: string): string {
  const labels: Record<string, string> = {
    queued: 'Queued',
    running: 'Running',
    awaiting_approval: 'Awaiting Approval',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled',
  }
  return status ? labels[status] || status : ''
}

function statusClass(status?: string): string {
  if (status === 'completed') return 'status-success'
  if (status === 'awaiting_approval') return 'status-warning'
  if (status === 'failed') return 'status-danger'
  if (status === 'running') return 'status-info'
  return 'status-secondary'
}

export default function CopilotMessageBubble({ message, run, selected, onSelectRun }: Props) {
  return (
    <article className={`copilot-message ${message.role === 'user' ? 'is-user' : 'is-assistant'} ${selected ? 'is-selected' : ''}`}>
      <div
        className="copilot-message__bubble"
        onClick={() => run?.id && onSelectRun?.(run.id)}
      >
        <div className="copilot-message__meta">
          <span>{message.role === 'user' ? 'You' : 'Account Copilot'}</span>
          {run && (
            <span className={`copilot-message__tag ${statusClass(run.status)}`}>
              {statusLabel(run.status)}
            </span>
          )}
        </div>
        <p className="copilot-message__content">{message.content}</p>
      </div>
    </article>
  )
}
