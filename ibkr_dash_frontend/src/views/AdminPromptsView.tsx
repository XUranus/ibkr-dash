import { useState, useEffect, useCallback, useMemo } from 'react'
import { fetchAdminPrompts, createAdminPrompt, fetchActivePrompt } from '@/api/adminPrompts'
import AdminTabs from '@/components/AdminTabs'
import type { PromptItem } from '@/types/adminPrompts'

export default function AdminPromptsView() {
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [prompts, setPrompts] = useState<PromptItem[]>([])
  const [selectedKey, setSelectedKey] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newContent, setNewContent] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      setPrompts(await fetchAdminPrompts())
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load prompts')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  const groupedPrompts = useMemo(() => {
    const groups: Record<string, PromptItem[]> = {}
    for (const p of prompts) {
      if (!groups[p.prompt_key]) groups[p.prompt_key] = []
      groups[p.prompt_key].push(p)
    }
    // Sort each group by version desc
    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => b.version - a.version)
    }
    return groups
  }, [prompts])

  const uniqueKeys = Object.keys(groupedPrompts).sort()
  const selectedVersions = selectedKey ? groupedPrompts[selectedKey] ?? [] : []
  const activeVersion = selectedVersions.find((v) => v.status === 'active') ?? null

  async function handleCreate() {
    if (!newKey.trim() || !newContent.trim()) return
    try {
      await createAdminPrompt({ prompt_key: newKey.trim(), content: newContent.trim() })
      setShowCreate(false)
      setNewKey('')
      setNewContent('')
      await loadData()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to create prompt')
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">Loading...</div></div></section>
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Prompt Management</h2>
              <p className="panel-subtitle">Manage prompt versions for AI agents.</p>
            </div>
            <button className="btn btn--accent btn--sm" onClick={() => setShowCreate(!showCreate)}>
              {showCreate ? 'Cancel' : 'New Prompt'}
            </button>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <section className="surface-panel" style={{ animation: 'slideUp 0.3s ease' }}>
          <div className="surface-panel__content">
            <p className="eyebrow">CREATE PROMPT</p>
            <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
              <label className="field-stack">
                <span className="field-stack__label">Prompt Key</span>
                <input className="input" value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="e.g. trade_decision_composer" />
              </label>
              <label className="field-stack">
                <span className="field-stack__label">Content</span>
                <textarea className="input" value={newContent} onChange={(e) => setNewContent(e.target.value)} rows={8} style={{ resize: 'vertical', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }} placeholder="Enter prompt content..." />
              </label>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <button className="btn btn--ghost" onClick={() => setShowCreate(false)}>Cancel</button>
                <button className="btn btn--accent" onClick={handleCreate} disabled={!newKey.trim() || !newContent.trim()}>Create</button>
              </div>
            </div>
          </div>
        </section>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--space-4)' }}>
        {/* Sidebar: prompt keys */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
          <div className="surface-panel__content" style={{ padding: '16px' }}>
            <p className="eyebrow" style={{ marginBottom: 8 }}>PROMPTS ({uniqueKeys.length})</p>
            <div style={{ display: 'grid', gap: 4 }}>
              {uniqueKeys.length === 0 ? (
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>No prompts found.</p>
              ) : (
                uniqueKeys.map((key) => (
                  <button
                    key={key}
                    className={`btn btn--ghost btn--sm ${selectedKey === key ? 'is-active' : ''}`}
                    onClick={() => setSelectedKey(key)}
                    style={{
                      justifyContent: 'flex-start',
                      textAlign: 'left',
                      borderRadius: 'var(--radius-sm)',
                      background: selectedKey === key ? 'rgba(212,168,67,0.08)' : 'transparent',
                      borderColor: selectedKey === key ? 'rgba(212,168,67,0.2)' : 'transparent',
                      color: selectedKey === key ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
                      fontSize: '0.82rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {key}
                    <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                      v{groupedPrompts[key][0]?.version ?? '?'}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Detail: versions */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
          <div className="surface-panel__content">
            {!selectedKey ? (
              <div className="empty-state" style={{ minHeight: 300 }}>Select a prompt from the list.</div>
            ) : (
              <>
                <p className="eyebrow">{selectedKey}</p>
                {activeVersion && (
                  <div style={{ marginTop: 8, marginBottom: 16, padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(61,214,140,0.15)', background: 'rgba(61,214,140,0.04)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span className="tag tag--positive">ACTIVE v{activeVersion.version}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{activeVersion.created_at}</span>
                    </div>
                    <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 300, overflow: 'auto' }}>
                      {activeVersion.content}
                    </pre>
                  </div>
                )}
                <p className="eyebrow" style={{ marginTop: 16 }}>ALL VERSIONS ({selectedVersions.length})</p>
                <div className="table-shell" style={{ marginTop: 8 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Status</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedVersions.map((v) => (
                        <tr key={v.id}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>v{v.version}</td>
                          <td><span className={`tag ${v.status === 'active' ? 'tag--positive' : v.status === 'archived' ? 'tag--warning' : ''}`}>{v.status}</span></td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{v.created_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </section>
  )
}
