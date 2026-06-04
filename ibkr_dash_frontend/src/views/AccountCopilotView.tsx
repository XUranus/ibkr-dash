import { useState, useEffect, useRef } from 'react'
import { listSessions, createSession, getSession, listMessages, sendMessage, sendMessageStream, listRunEvents, getRun, listSessionMemories } from '@/api/accountCopilot'
import type { CopilotSession, CopilotMessage, CopilotRun, CopilotMemory, CopilotEvent } from '@/types/accountCopilot'

const welcomeGroups = [
  { title: 'Account Facts', questions: ['What is my current risk level?', 'Which stocks caused my recent losses?', 'Is my cash allocation reasonable?'] },
  { title: 'Trade Review', questions: ['How has my AMD trading history performed?', 'Do I tend to sell too early?'] },
  { title: 'Market Research', questions: ['Why has AMD been moving recently?', 'Any recent news on Xiaomi?'] },
  { title: 'Decision Support', questions: ['Is MU a good time to build a position?', 'Should I continue holding AMD?'] },
]

export default function AccountCopilotView() {
  const [sessions, setSessions] = useState<CopilotSession[]>([])
  const [activeSession, setActiveSession] = useState<CopilotSession | null>(null)
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [runsById, setRunsById] = useState<Record<string, CopilotRun>>({})
  const [inputText, setInputText] = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  async function loadSessions() {
    setLoadingSessions(true)
    try {
      const items = await listSessions(100)
      setSessions(items)
      if (!activeSession && items.length > 0) await selectSession(items[0].id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load sessions')
    } finally {
      setLoadingSessions(false)
    }
  }

  async function createNewSession() {
    try {
      const session = await createSession({ title: 'New Chat' })
      setSessions((prev) => [session, ...prev])
      await selectSession(session.id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to create session')
    }
  }

  async function selectSession(sessionId: string) {
    setErrorMessage('')
    setLoadingMessages(true)
    try {
      const session = await getSession(sessionId)
      setActiveSession(session)
      const msgs = await listMessages(sessionId, 200)
      setMessages(msgs)
      const runIds = Array.from(new Set(msgs.map((m) => m.run_id).filter(Boolean))) as string[]
      const runs: Record<string, CopilotRun> = {}
      await Promise.all(runIds.map(async (rid) => {
        try { runs[rid] = await getRun(rid) } catch { /* ignore */ }
      }))
      setRunsById(runs)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load messages')
    } finally {
      setLoadingMessages(false)
    }
  }

  async function sendCurrentMessage() {
    const content = inputText.trim()
    if (!content || sending) return
    setSending(true)
    setErrorMessage('')
    try {
      let session = activeSession
      if (!session) {
        session = await createSession({ title: content.slice(0, 24) })
        setActiveSession(session)
        setSessions((prev) => [session!, ...prev])
      }
      try {
        const response = await sendMessageStream(session.id, content)
        const userMsg = response.user_message
        const assistantMsg: CopilotMessage = {
          id: `live_${response.run.id}`,
          session_id: session.id,
          role: 'assistant',
          content: 'Analyzing...',
          created_at: new Date().toISOString(),
          run_id: response.run.id,
          metadata: { live: true },
        }
        setMessages((prev) => [...prev, userMsg, assistantMsg])
        setRunsById((prev) => ({ ...prev, [response.run.id]: { ...response.run, _streaming: true } }))
        setInputText('')
      } catch {
        const response = await sendMessage(session.id, content)
        setMessages((prev) => [...prev, response.user_message, response.assistant_message])
        setRunsById((prev) => ({ ...prev, [response.run.id]: response.run }))
        setInputText('')
      }
      void loadSessions()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  useEffect(() => { void loadSessions() }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const hasMessages = messages.length > 0

  return (
    <main style={{
      display: 'flex', alignItems: 'stretch',
      height: 'calc(100vh - 180px)', minHeight: 640,
      marginTop: 24, maxWidth: 1720, width: '100%', margin: '24px auto 0',
      color: '#e2e8f0',
      border: '1px solid rgba(125, 211, 252, 0.15)',
      borderRadius: 18,
      background: 'linear-gradient(135deg, rgba(2, 6, 23, 0.94), rgba(15, 23, 42, 0.9))',
      boxShadow: '0 24px 80px rgba(0, 0, 0, 0.32)',
      overflow: 'hidden',
    }}>
      {/* Session Sidebar */}
      <aside style={{
        width: 300, minWidth: 300, flexShrink: 0,
        borderRight: '1px solid rgba(125, 211, 252, 0.14)',
        background: 'rgba(2, 8, 23, 0.72)',
        display: 'grid', gridTemplateRows: 'auto 1fr',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid rgba(125, 211, 252, 0.13)' }}>
          <button className="btn btn--accent" onClick={createNewSession} style={{ width: '100%' }}>+ New Chat</button>
        </div>
        <div style={{ overflow: 'auto', padding: 8 }}>
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => selectSession(s.id)}
              style={{
                width: '100%', padding: '12px 14px', marginBottom: 6,
                borderRadius: 12, border: `1px solid ${activeSession?.id === s.id ? 'rgba(34, 211, 238, 0.5)' : 'rgba(125, 211, 252, 0.1)'}`,
                background: activeSession?.id === s.id ? 'rgba(34, 211, 238, 0.08)' : 'transparent',
                color: '#e2e8f0', cursor: 'pointer', textAlign: 'left',
              }}
            >
              <div style={{ fontSize: '0.92rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: 4 }}>{s.message_count} messages</div>
            </button>
          ))}
        </div>
      </aside>

      {/* Chat Area */}
      <section style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, overflow: 'hidden' }}>
        <header style={{ padding: '22px 24px', borderBottom: '1px solid rgba(125, 211, 252, 0.13)', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ margin: '0 0 5px', color: '#22d3ee', fontSize: '0.72rem', textTransform: 'uppercase' }}>Account Copilot</p>
            <h1 style={{ margin: 0, fontSize: '1.45rem' }}>{activeSession?.title || 'Account Copilot'}</h1>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span className="tag tag--positive">IBKR Data</span>
            <span className="tag tag--accent">Public Market</span>
          </div>
        </header>

        {errorMessage && <div style={{ flexShrink: 0, margin: '14px 24px 0', padding: '10px 12px', color: '#fecaca', border: '1px solid rgba(248, 113, 113, 0.35)', borderRadius: 12, background: 'rgba(127, 29, 29, 0.32)' }}>{errorMessage}</div>}

        {!hasMessages && !loadingMessages ? (
          <div style={{ flex: 1, overflow: 'auto', margin: 24, padding: 22, border: '1px solid rgba(125, 211, 252, 0.15)', borderRadius: 18, background: 'rgba(15, 23, 42, 0.58)' }}>
            <p style={{ margin: '0 0 5px', color: '#22d3ee', fontSize: '0.72rem', textTransform: 'uppercase' }}>Welcome</p>
            <h2 style={{ maxWidth: 760, margin: '0 0 18px', fontSize: '1.35rem', lineHeight: 1.5 }}>
              Ask questions about your account, positions, trades, and risk in natural language.
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
              {welcomeGroups.map((group) => (
                <section key={group.title}>
                  <h3 style={{ margin: '0 0 8px', color: '#93c5fd', fontSize: '0.82rem' }}>{group.title}</h3>
                  {group.questions.map((q) => (
                    <button key={q} onClick={() => setInputText(q)} style={{
                      display: 'block', width: '100%', padding: 12, marginBottom: 6,
                      color: '#dff7ff', textAlign: 'left',
                      border: '1px solid rgba(125, 211, 252, 0.16)', borderRadius: 14,
                      background: 'rgba(2, 8, 23, 0.52)', cursor: 'pointer',
                    }}>{q}</button>
                  ))}
                </section>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, overflow: 'auto', padding: '18px 24px' }}>
            {loadingMessages ? (
              <div style={{ color: '#94a3b8', textAlign: 'center', padding: 40 }}>Loading messages...</div>
            ) : messages.map((msg) => (
              <div key={msg.id} style={{
                marginBottom: 16, padding: '14px 18px', borderRadius: 16,
                background: msg.role === 'user' ? 'rgba(30, 58, 138, 0.3)' : 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(125, 211, 252, 0.1)'}`,
                maxWidth: '85%',
                marginLeft: msg.role === 'user' ? 'auto' : 0,
              }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: 6, textTransform: 'uppercase' }}>
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div style={{ flexShrink: 0, padding: '18px 24px 22px', borderTop: '1px solid rgba(125, 211, 252, 0.13)' }}>
          <form style={{ display: 'flex', gap: 12 }} onSubmit={(e) => { e.preventDefault(); sendCurrentMessage() }}>
            <input
              className="input"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask about your portfolio, trades, or market..."
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn--accent" disabled={sending || !inputText.trim()}>
              {sending ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
