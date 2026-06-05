import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { listSessions, chat, listMessages, deleteSession } from '@/api/accountCopilot'
import type { CopilotSession, CopilotMessage } from '@/api/accountCopilot'

export default function AccountCopilotView() {
  const { t } = useTranslation()
  const [sessions, setSessions] = useState<CopilotSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const welcomeQuestions = t('copilot.welcomeQuestions', { returnObjects: true }) as string[]

  const loadSessions = useCallback(async () => {
    try {
      const items = await listSessions(50)
      setSessions(items)
    } catch {
      // Silent fail
    }
  }, [])

  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const items = await listMessages(sessionId)
      setMessages(items)
    } catch {
      setMessages([])
    }
  }, [])

  useEffect(() => { void loadSessions() }, [loadSessions])

  useEffect(() => {
    if (activeSessionId) void loadMessages(activeSessionId)
    else setMessages([])
  }, [activeSessionId, loadMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(text?: string) {
    const content = (text ?? inputText).trim()
    if (!content || sending) return

    setInputText('')
    setSending(true)
    setErrorMessage('')

    // Optimistic: add user message
    const userMsg: CopilotMessage = {
      id: Date.now(),
      session_id: activeSessionId ?? '',
      role: 'user',
      content,
      metadata: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const response = await chat(activeSessionId, content)

      // Update session if new
      if (!activeSessionId || response.session_id !== activeSessionId) {
        setActiveSessionId(response.session_id)
      }

      // Add assistant message
      const assistantMsg: CopilotMessage = {
        id: Date.now() + 1,
        session_id: response.session_id,
        role: 'assistant',
        content: response.answer,
        metadata: { run_id: response.run_id, tool_calls: response.tool_calls },
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev.slice(0, -1), userMsg, assistantMsg])

      // Reload sessions to pick up new one
      void loadSessions()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('copilot.failedToSend'))
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setSending(false)
    }
  }

  async function handleNewChat() {
    setActiveSessionId(null)
    setMessages([])
    setInputText('')
    setErrorMessage('')
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setMessages([])
      }
    } catch {
      // Silent fail
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  function sessionDisplayName(s: CopilotSession): string {
    if (s.title && s.title.trim()) return s.title
    return `Session ${s.session_id.slice(0, 8)}`
  }

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <div style={{ display: 'grid', gridTemplateColumns: sidebarOpen ? '280px 1fr' : '1fr', gap: 'var(--space-4)', minHeight: '70vh' }}>
        {/* Sidebar */}
        {sidebarOpen && (
          <section className="surface-panel">
            <div className="surface-panel__content" style={{ padding: '16px', display: 'grid', gap: 10, alignContent: 'start' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <p className="eyebrow" style={{ margin: 0 }}>{t('copilot.sessions').toUpperCase()}</p>
                <button className="btn btn--ghost btn--sm" onClick={handleNewChat} style={{ fontSize: '0.78rem' }}>{t('copilot.newChat')}</button>
              </div>
              <div style={{ display: 'grid', gap: 4, maxHeight: '60vh', overflow: 'auto' }}>
                {sessions.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('copilot.noSessions')}</p>
                ) : (
                  sessions.map((s) => (
                    <div key={s.session_id} style={{ display: 'flex', gap: 4 }}>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => setActiveSessionId(s.session_id)}
                        style={{
                          flex: 1, justifyContent: 'flex-start', textAlign: 'left',
                          borderRadius: 'var(--radius-sm)',
                          background: activeSessionId === s.session_id ? 'rgba(212,168,67,0.08)' : 'transparent',
                          borderColor: activeSessionId === s.session_id ? 'rgba(212,168,67,0.2)' : 'transparent',
                          color: activeSessionId === s.session_id ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
                          fontSize: '0.82rem',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                        {sessionDisplayName(s)}
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => handleDeleteSession(s.session_id)}
                        title="Delete session"
                        style={{
                          minWidth: 28,
                          padding: 0,
                          fontSize: '0.75rem',
                          color: 'var(--color-text-muted)',
                          opacity: 0.6,
                          transition: 'opacity 0.15s, color 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = 'var(--color-negative)' }}
                        onMouseLeave={e => { e.currentTarget.style.opacity = '0.6'; e.currentTarget.style.color = 'var(--color-text-muted)' }}
                      >
                        ✕
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>
        )}

        {/* Chat area */}
        <section className="surface-panel">
          <div className="surface-panel__content" style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', minHeight: '65vh', padding: '16px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <button className="btn btn--ghost btn--sm" onClick={() => setSidebarOpen(!sidebarOpen)} style={{ fontSize: '0.75rem' }}>
                {sidebarOpen ? `◀ ${t('copilot.hide')}` : `▶ ${t('copilot.showSessions')}`}
              </button>
              {activeSessionId && (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                  {activeSessionId.slice(0, 12)}...
                </span>
              )}
            </div>

            {/* Messages */}
            <div style={{ overflow: 'auto', display: 'grid', gap: 12, alignContent: 'start', paddingRight: 4 }}>
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <p className="eyebrow" style={{ marginBottom: 12 }}>{t('copilot.welcome')}</p>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: 16 }}>{t('copilot.welcomeDesc')}</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                    {welcomeQuestions.map((q) => (
                      <button key={q} className="btn btn--ghost btn--sm" onClick={() => void handleSend(q)}
                        style={{ fontSize: '0.8rem', borderRadius: 'var(--radius-sm)' }}>
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}>
                  <div style={{
                    maxWidth: '85%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: msg.role === 'user' ? 'rgba(212,168,67,0.12)' : 'rgba(10,14,26,0.5)',
                    border: `1px solid ${msg.role === 'user' ? 'rgba(212,168,67,0.2)' : 'var(--color-border-subtle)'}`,
                  }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                      {msg.role}
                    </div>
                    {msg.role === 'user' ? (
                      <div style={{ fontSize: '0.88rem', color: 'var(--color-text-primary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </div>
                    ) : (
                      <div className="copilot-markdown" style={{ fontSize: '0.88rem', color: 'var(--color-text-primary)', lineHeight: 1.6 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.5)', border: '1px solid var(--color-border-subtle)' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>{t('copilot.thinking')}</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div style={{ marginTop: 12, borderTop: '1px solid var(--color-border-subtle)', paddingTop: 12 }}>
              {errorMessage && (
                <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', marginBottom: 8 }}>{errorMessage}</p>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <textarea
                  className="input"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={t('copilot.placeholder')}
                  rows={2}
                  style={{ resize: 'none', flex: 1 }}
                />
                <button className="btn btn--accent" onClick={() => void handleSend()} disabled={sending || !inputText.trim()}>
                  {t('copilot.send')}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </section>
  )
}
