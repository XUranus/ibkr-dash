/** Copilot memory panel -- displays saved copilot memories. */

interface Memory {
  id: string
  memory_type: string
  content: string
  status?: string
  created_at?: string
}

interface Props {
  memories: Memory[]
  className?: string
}

export default function CopilotMemoryPanel({ memories, className }: Props) {
  if (!memories.length) {
    return (
      <div className={`copilot-memory ${className || ''}`}>
        <h4>Memories</h4>
        <p className="copilot-memory__empty">No memories saved yet.</p>
      </div>
    )
  }

  return (
    <div className={`copilot-memory ${className || ''}`}>
      <h4>Memories</h4>
      <ul className="copilot-memory__list">
        {memories.map((m) => (
          <li key={m.id} className={`copilot-memory__item ${m.status === 'archived' ? 'is-archived' : ''}`}>
            <span className="copilot-memory__type">{m.memory_type}</span>
            <span className="copilot-memory__content">{m.content}</span>
            {m.created_at && (
              <span className="copilot-memory__date">
                {new Date(m.created_at).toLocaleDateString()}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
