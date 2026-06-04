import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  activateAdminPromptVersion,
  createAdminPromptVersion,
  createAdminPromptVersionFromCodeDefault,
  fetchAdminPromptDetail,
  fetchAdminPrompts,
  fetchAdminRuntimePrompt,
  seedDefaultAdminPrompts,
  syncCodeDefaultAdminPrompts,
} from '@/api/adminPrompts'
import AdminTabs from '@/components/AdminTabs'
import type { PromptDetailResponse, PromptListItem, PromptRuntimeResponse, PromptStatus, PromptVersion } from '@/types/adminPrompts'

export default function AdminPromptsView() {
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncingSingle, setSyncingSingle] = useState(false)
  const [runtimeLoading, setRuntimeLoading] = useState(false)
  const [activatingVersion, setActivatingVersion] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [prompts, setPrompts] = useState<PromptListItem[]>([])
  const [selectedKey, setSelectedKey] = useState('')
  const [detail, setDetail] = useState<PromptDetailResponse | null>(null)
  const [runtimePrompt, setRuntimePrompt] = useState<PromptRuntimeResponse | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null)
  const [showDefaultContent, setShowDefaultContent] = useState(false)
  const [draftContent, setDraftContent] = useState('')
  const [changeNote, setChangeNote] = useState('')

  const selectedPrompt = prompts.find((item) => item.prompt_key === selectedKey) ?? null
  const versions = detail?.versions ?? []
  const activeVersion = detail?.active ?? null
  const canSaveDraft = Boolean(selectedKey && draftContent.trim() && !saving)

  const groupedPrompts = useMemo(() => {
    const groups = new Map<string, PromptListItem[]>()
    for (const item of prompts) {
      const key = item.module_name || 'other'
      groups.set(key, [...(groups.get(key) ?? []), item])
    }
    return Array.from(groups.entries()).map(([moduleName, items]) => ({ moduleName, items }))
  }, [prompts])

  function shortHash(value: string | null | undefined, length = 8): string {
    return value ? value.slice(0, length) : '--'
  }

  function formatDate(value: string | null | undefined): string {
    if (!value) return '--'
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
  }

  function statusClass(status: PromptStatus): string {
    if (status === 'active') return 'tag-positive'
    if (status === 'archived') return 'tag-negative'
    return 'tag-accent'
  }

  const loadPrompts = useCallback(async (nextSelectedKey?: string) => {
    setLoading(true)
    setErrorMessage('')
    try {
      const items = await fetchAdminPrompts()
      setPrompts(items)
      const nextKey = nextSelectedKey || selectedKey || items[0]?.prompt_key || ''
      if (nextKey) await selectPrompt(nextKey, items)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load prompts')
    } finally {
      setLoading(false)
    }
  }, [selectedKey])

  async function selectPrompt(promptKey: string, promptList?: PromptListItem[]): Promise<void> {
    setSelectedKey(promptKey)
    setDetailLoading(true)
    setRuntimePrompt(null)
    setSelectedVersion(null)
    setErrorMessage('')
    try {
      const d = await fetchAdminPromptDetail(promptKey)
      setDetail(d)
      setDraftContent(d.active?.content ?? d.definition.default_content)
      setChangeNote('')
    } catch (error) {
      setDetail(null)
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load prompt detail')
    } finally {
      setDetailLoading(false)
    }
  }

  async function seedDefaults(): Promise<void> {
    setSeeding(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await seedDefaultAdminPrompts()
      setNoticeMessage(response.message)
      await loadPrompts(selectedKey)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Seed failed')
    } finally {
      setSeeding(false)
    }
  }

  async function syncAllCodeDefaults(): Promise<void> {
    setSyncing(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await syncCodeDefaultAdminPrompts()
      setNoticeMessage(response.message)
      await loadPrompts(selectedKey)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  async function createFromCodeDefault(): Promise<void> {
    if (!selectedKey) return
    setSyncingSingle(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await createAdminPromptVersionFromCodeDefault(selectedKey)
      setNoticeMessage(response.message)
      await loadPrompts(selectedKey)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Create from code default failed')
    } finally {
      setSyncingSingle(false)
    }
  }

  async function saveNewVersion(): Promise<void> {
    if (!selectedKey || !draftContent.trim()) return
    setSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await createAdminPromptVersion(selectedKey, { content: draftContent.trim(), change_note: changeNote.trim() || undefined })
      setNoticeMessage(response.message)
      await loadPrompts(selectedKey)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function activateVersion(version: PromptVersion): Promise<void> {
    if (version.status === 'active' || !selectedKey) return
    if (!window.confirm(`Activate ${version.version}? Current active version will be archived.`)) return
    const note = window.prompt('Optional: activation note', version.change_note ?? '') ?? ''
    setActivatingVersion(version.version)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const response = await activateAdminPromptVersion(selectedKey, version.version, { change_note: note.trim() || undefined })
      setNoticeMessage(response.message)
      await loadPrompts(selectedKey)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Activation failed')
    } finally {
      setActivatingVersion('')
    }
  }

  async function viewRuntimePrompt(): Promise<void> {
    if (!selectedKey) return
    setRuntimeLoading(true)
    setRuntimePrompt(null)
    setErrorMessage('')
    try {
      setRuntimePrompt(await fetchAdminRuntimePrompt(selectedKey))
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load runtime prompt')
    } finally {
      setRuntimeLoading(false)
    }
  }

  useEffect(() => { void loadPrompts() }, [])

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Agent Prompt Management</h2>
              <p className="panel-subtitle">Manage system prompts for all agents and sub-agents.</p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn--ghost" disabled={seeding} onClick={() => void seedDefaults()}>{seeding ? 'Seeding...' : 'Seed Defaults'}</button>
              <button className="btn btn--accent" disabled={syncing} onClick={() => void syncAllCodeDefaults()}>{syncing ? 'Syncing...' : 'Sync All Code Defaults'}</button>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section>
      ) : (
        <>
          {noticeMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-positive)', background: 'rgba(9, 47, 39, 0.48)', border: '1px solid rgba(52, 210, 163, 0.18)' }}>{noticeMessage}</p>}
          {errorMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-negative)', background: 'rgba(55, 18, 28, 0.48)', border: '1px solid rgba(255, 107, 122, 0.18)' }}>{errorMessage}</p>}

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 0.78fr) minmax(0, 1.45fr)', gap: 'var(--space-4)', alignItems: 'start' }}>
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Prompt List</h3>
                <p className="panel-subtitle">Click an item to view versions and runtime content.</p>
                <div style={{ display: 'grid', gap: 10 }}>
                  {groupedPrompts.map((group) => (
                    <section key={group.moduleName}>
                      <h4 style={{ margin: '0 0 10px', color: 'var(--color-text-primary)' }}>{group.moduleName}</h4>
                      <div style={{ display: 'grid', gap: 10 }}>
                        {group.items.map((item) => (
                          <button key={item.prompt_key} type="button" style={{ width: '100%', display: 'grid', gap: 10, padding: 14, textAlign: 'left', color: 'var(--color-text-primary)', border: `1px solid ${item.prompt_key === selectedKey ? 'rgba(89, 201, 165, 0.45)' : 'rgba(129, 160, 207, 0.14)'}`, borderRadius: 'var(--radius-md)', background: item.prompt_key === selectedKey ? 'rgba(89, 201, 165, 0.08)' : 'rgba(10, 18, 32, 0.5)', cursor: 'pointer' }} onClick={() => void selectPrompt(item.prompt_key)}>
                            <div style={{ display: 'grid', gap: 6 }}>
                              <strong>{item.display_name}</strong>
                              <small style={{ color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>{item.module_name} / {item.agent_name}</small>
                              <code style={{ color: 'var(--color-accent)', overflowWrap: 'anywhere', fontSize: '0.82rem' }}>{item.prompt_key}</code>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>
                              <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600, background: item.has_active ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: item.has_active ? 'var(--color-positive)' : 'var(--color-negative)' }}>{item.has_active ? item.active_version || 'ACTIVE' : 'NO ACTIVE'}</span>
                              <span>active #{shortHash(item.active_content_hash)}</span>
                              <span>code #{shortHash(item.code_default_hash)}</span>
                              <span>{formatDate(item.active_updated_at)}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </div>
            </section>

            <section className="surface-panel">
              <div className="surface-panel__content">
                {detailLoading ? (
                  <div className="empty-state">Loading...</div>
                ) : detail ? (
                  <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                    <div className="section-header">
                      <div>
                        <h3 className="panel-title">{detail.definition.display_name}</h3>
                        <p className="panel-subtitle">{detail.definition.description}</p>
                      </div>
                      <button className="btn btn--ghost" disabled={runtimeLoading} onClick={() => void viewRuntimePrompt()}>{runtimeLoading ? 'Loading...' : 'View Runtime Prompt'}</button>
                    </div>

                    <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, margin: 0 }}>
                      {[['prompt_key', detail.definition.prompt_key], ['module', detail.definition.module_name], ['agent', detail.definition.agent_name], ['active', activeVersion?.version ?? 'None'], ['active hash', shortHash(activeVersion?.content_hash, 12)], ['code default hash', shortHash(selectedPrompt?.code_default_hash, 12)], ['matches code default', selectedPrompt?.matches_code_default ? 'Yes' : 'No']].map(([k, v]) => (
                        <div key={k} style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
                          <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>{k}</dt>
                          <dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{String(v)}</dd>
                        </div>
                      ))}
                    </dl>

                    {runtimePrompt && (
                      <div style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                          <h4 style={{ margin: 0 }}>Runtime Prompt</h4>
                          <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{runtimePrompt.metadata.source}</span>
                          <code style={{ color: 'var(--color-accent)', fontSize: '0.82rem' }}>#{shortHash(runtimePrompt.metadata.content_hash, 12)}</code>
                        </div>
                        <pre style={{ maxHeight: 520, overflow: 'auto', padding: 14, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', lineHeight: 1.55, color: 'var(--color-text-primary)', background: 'rgba(10, 18, 32, 0.85)', borderRadius: 12, border: '1px solid rgba(129, 160, 207, 0.16)' }}>{runtimePrompt.content}</pre>
                      </div>
                    )}

                    <div style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <h4 style={{ margin: 0 }}>Create New Version</h4>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button className="btn btn--ghost btn--sm" disabled={syncingSingle} onClick={() => void createFromCodeDefault()}>{syncingSingle ? '...' : 'From Code Default'}</button>
                          <button className="btn btn--ghost btn--sm" disabled={!activeVersion} onClick={() => setDraftContent(activeVersion?.content ?? '')}>Copy Active</button>
                          <button className="btn btn--ghost btn--sm" onClick={() => setDraftContent(detail.definition.default_content)}>Copy Code Default</button>
                        </div>
                      </div>
                      <textarea className="input" style={{ minHeight: 320, fontFamily: 'monospace', lineHeight: 1.55, resize: 'vertical' as const }} value={draftContent} onChange={(e) => setDraftContent(e.target.value)} placeholder="Enter new version prompt content" />
                      <div style={{ display: 'flex', gap: 10, alignItems: 'stretch', marginTop: 10 }}>
                        <input className="input" style={{ flex: 1 }} value={changeNote} onChange={(e) => setChangeNote(e.target.value)} placeholder="change_note (optional)" />
                        <button className="btn btn--accent" disabled={!canSaveDraft} onClick={() => void saveNewVersion()}>{saving ? 'Saving...' : 'Save as New Version'}</button>
                      </div>
                    </div>

                    <div style={{ padding: 14, border: '1px solid rgba(129, 160, 207, 0.12)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.46)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <h4 style={{ margin: 0 }}>Version History</h4>
                        <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{versions.length} versions</span>
                      </div>
                      {versions.length > 0 ? (
                        <div className="table-shell" style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse' }}>
                            <thead>
                              <tr>{['Version', 'Status', 'Default', 'Hash', 'Created By', 'Created', 'Updated', 'Note', 'Actions'].map((h) => <th key={h} style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.78rem', textTransform: 'uppercase' }}>{h}</th>)}</tr>
                            </thead>
                            <tbody>
                              {versions.map((v) => (
                                <tr key={v.id}>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{v.version}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}><span className={statusClass(v.status)} style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', fontWeight: 600 }}>{v.status.toUpperCase()}</span></td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{v.is_default ? 'YES' : 'NO'}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}><code style={{ color: 'var(--color-accent)' }}>{shortHash(v.content_hash, 12)}</code></td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{v.created_by || '--'}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{formatDate(v.created_at)}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>{formatDate(v.updated_at)}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)', maxWidth: 260 }}>{v.change_note || '--'}</td>
                                  <td style={{ padding: '12px', borderBottom: '1px solid rgba(129, 160, 207, 0.1)' }}>
                                    <div style={{ display: 'flex', gap: 8 }}>
                                      <button className="btn btn--ghost btn--sm" onClick={() => setSelectedVersion(v)}>View</button>
                                      <button className="btn btn--ghost btn--sm" disabled={v.status === 'active' || activatingVersion === v.version} onClick={() => void activateVersion(v)}>{activatingVersion === v.version ? '...' : 'Activate'}</button>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="empty-state">No versions. Seed defaults first.</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">Select a prompt from the list.</div>
                )}
              </div>
            </section>
          </div>
        </>
      )}

      {selectedVersion && (
        <div className="admin-dialog-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setSelectedVersion(null) }}>
          <section className="surface-panel admin-dialog" style={{ width: 'min(980px, calc(100vw - 32px))' }}>
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <p className="eyebrow">{selectedVersion.version}</p>
                  <h3 className="panel-title">{selectedVersion.display_name}</h3>
                </div>
                <button className="btn btn--ghost" onClick={() => setSelectedVersion(null)}>X</button>
              </div>
              <pre style={{ maxHeight: 520, overflow: 'auto', padding: 14, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', lineHeight: 1.55, color: 'var(--color-text-primary)', background: 'rgba(10, 18, 32, 0.85)', borderRadius: 12, border: '1px solid rgba(129, 160, 207, 0.16)' }}>{selectedVersion.content}</pre>
            </div>
          </section>
        </div>
      )}
    </section>
  )
}
