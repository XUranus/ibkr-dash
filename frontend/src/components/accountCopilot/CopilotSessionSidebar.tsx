/** Copilot session sidebar -- session list, create, rename. */

import { useMemo, useState } from 'react'
import type { CopilotSession } from '../../types/accountCopilot'

const MAX_VISIBLE = 6

interface Props {
  sessions: CopilotSession[]
  activeSessionId?: string
  loading?: boolean
  renameTitle: string
  onCreate: () => void
  onSelect: (sessionId: string) => void
  onRename: () => void
  onArchive: () => void
  onRenameTitleChange: (value: string) => void
}

export default function CopilotSessionSidebar({
  sessions,
  activeSessionId,
  loading,
  renameTitle,
  onCreate,
  onSelect,
  onRename,
  onArchive,
  onRenameTitleChange,
}: Props) {
  const [showAll, setShowAll] = useState(false)

  const activeIsHidden = useMemo(() => {
    if (!activeSessionId || showAll) return false
    const idx = sessions.findIndex((s) => s.id === activeSessionId)
    return idx >= MAX_VISIBLE
  }, [sessions, activeSessionId, showAll])

  const visibleSessions = useMemo(() => {
    if (showAll || activeIsHidden) return sessions
    return sessions.slice(0, MAX_VISIBLE)
  }, [sessions, showAll, activeIsHidden])

  const hiddenCount = Math.max(0, sessions.length - MAX_VISIBLE)

  function formatDate(value?: string | null): string {
    if (!value) return '--'
    return new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value))
  }

  return (
    <aside className="copilot-sidebar">
      <div className="copilot-sidebar__header">
        <div>
          <p className="copilot-sidebar__eyebrow">Account Copilot</p>
          <h2>Sessions</h2>
        </div>
        <button className="copilot-sidebar__btn-create" onClick={onCreate} title="New session">
          +
        </button>
      </div>

      <div className="copilot-sidebar__editor">
        <input
          type="text"
          value={renameTitle}
          placeholder="Session title"
          onChange={(e) => onRenameTitleChange(e.target.value)}
          className="copilot-sidebar__input"
        />
        <div className="copilot-sidebar__editor-actions">
          <button className="copilot-sidebar__btn" onClick={onRename}>
            Rename
          </button>
          <button className="copilot-sidebar__btn copilot-sidebar__btn--ghost" onClick={onArchive}>
            Archive
          </button>
        </div>
      </div>

      {loading ? (
        <div className="copilot-sidebar__state">Loading sessions...</div>
      ) : (
        visibleSessions.map((session) => (
          <button
            key={session.id}
            className={`copilot-sidebar__session ${session.id === activeSessionId ? 'is-active' : ''} ${session.status === 'archived' ? 'is-archived' : ''}`}
            onClick={() => onSelect(session.id)}
          >
            <span className="copilot-sidebar__session-title">{session.title || 'Untitled'}</span>
            <span className="copilot-sidebar__session-meta">
              {formatDate(session.updated_at)}
              {session.status === 'archived' && <span className="copilot-sidebar__badge">archived</span>}
            </span>
          </button>
        ))
      )}

      {hiddenCount > 0 && !activeIsHidden && (
        <button className="copilot-sidebar__toggle" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Collapse' : `Show more (${hiddenCount})`}
        </button>
      )}
    </aside>
  )
}
