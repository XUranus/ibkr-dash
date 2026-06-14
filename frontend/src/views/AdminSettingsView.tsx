import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchAllSettings, updateSettings, resetSettings, type SettingItem, type SettingsByCategory } from '@/api/adminSettings'
import { testIbkrConnection } from '@/api/adminIbkr'
import { testLlmProvider } from '@/api/adminLlm'
import { fetchEmailSettings, updateEmailSettings, sendEmailTest } from '@/api/adminEmail'
import { logout } from '@/api/auth'
import AdminTabs from '@/components/AdminTabs'
import type { IbkrTestResponse } from '@/types/adminIbkr'
import type { LlmProviderTestResponse } from '@/types/adminLlm'
import type { EmailSettings, EmailTestResponse } from '@/types/adminEmail'

/* ---------- toggle switch styles ---------- */
const switchStyle: React.CSSProperties = {
  position: 'relative', width: 36, height: 20, flexShrink: 0,
  borderRadius: 10, cursor: 'pointer', transition: 'background 0.2s',
}
const switchKnob: React.CSSProperties = {
  position: 'absolute', top: 2, width: 16, height: 16, borderRadius: '50%',
  background: 'var(--color-surface-raised)', transition: 'left 0.2s',
}

/** Unified accordion: track which single section is open. null = all collapsed. */
function useAccordion(initial: string | null = null) {
  const [expanded, setExpanded] = useState<string | null>(initial)
  function toggle(key: string) {
    setExpanded((prev) => (prev === key ? null : key))
  }
  return { expanded, toggle }
}

export default function AdminSettingsView() {
  const { t } = useTranslation()
  const { expanded, toggle } = useAccordion()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<SettingsByCategory>({})
  // edits: key → { value, category }
  const [edits, setEdits] = useState<Record<string, { value: string; category: string }>>({})

  // Per-category saving state
  const [savingCats, setSavingCats] = useState<Record<string, boolean>>({})

  // IBKR test state
  const [ibkrTesting, setIbkrTesting] = useState(false)
  const [ibkrTestResult, setIbkrTestResult] = useState<IbkrTestResponse | null>(null)

  // LLM test state
  const [llmTesting, setLlmTesting] = useState(false)
  const [llmTestPrompt, setLlmTestPrompt] = useState('Please reply with OK')
  const [llmTestResult, setLlmTestResult] = useState<LlmProviderTestResponse | null>(null)

  // Email state
  const [emailLoading, setEmailLoading] = useState(true)
  const [emailSaving, setEmailSaving] = useState(false)
  const [emailTesting, setEmailTesting] = useState(false)
  const [emailSettings, setEmailSettings] = useState<EmailSettings | null>(null)
  const [emailTestResult, setEmailTestResult] = useState<EmailTestResponse | null>(null)
  const [emailForm, setEmailForm] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_address: '',
    to_addresses: '',
    enabled: false,
  })

  // Track which categories have pending edits
  const dirtyCategories = useMemo(() => {
    const cats = new Set<string>()
    for (const edit of Object.values(edits)) {
      cats.add(edit.category)
    }
    return cats
  }, [edits])

  const hasAnyEdits = dirtyCategories.size > 0

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await fetchAllSettings()
      setSettings(data)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  const loadEmailData = useCallback(async () => {
    setEmailLoading(true)
    try {
      const s = await fetchEmailSettings()
      setEmailSettings(s)
      setEmailForm({
        smtp_host: s.smtp_host ?? '',
        smtp_port: s.smtp_port ?? 587,
        smtp_username: s.smtp_username ?? '',
        smtp_password: '',
        from_address: s.from_address ?? '',
        to_addresses: s.to_addresses?.join(', ') ?? '',
        enabled: s.enabled,
      })
    } catch {
      // email may not be configured; silently ignore
    } finally {
      setEmailLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])
  useEffect(() => { void loadEmailData() }, [loadEmailData])

  function handleEdit(key: string, value: string, category: string) {
    setEdits((prev) => ({ ...prev, [key]: { value, category } }))
  }

  /** Save edits for a specific category */
  async function handleCategorySave(cat: string) {
    const catEdits: Record<string, string> = {}
    for (const [key, edit] of Object.entries(edits)) {
      if (edit.category === cat) catEdits[key] = edit.value
    }
    if (Object.keys(catEdits).length === 0) return

    const passwordChanged = 'AUTH_PASSWORD' in catEdits

    setSavingCats((prev) => ({ ...prev, [cat]: true }))
    setErrorMessage('')
    setNoticeMessage('')
    try {
      await updateSettings(catEdits)

      if (passwordChanged) {
        try { await logout() } catch { /* expected */ }
        window.location.href = '/'
        return
      }

      setEdits((prev) => {
        const next = { ...prev }
        for (const key of Object.keys(catEdits)) delete next[key]
        return next
      })
      setNoticeMessage(t('adminSettings.saved'))
      await loadData()
    } catch (err) {
      // If password was changed, save may have succeeded but session is now invalid — redirect
      if (passwordChanged) {
        try { await logout() } catch { /* expected */ }
        window.location.href = '/'
        return
      }
      setErrorMessage(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setSavingCats((prev) => ({ ...prev, [cat]: false }))
    }
  }

  /** Save all pending edits across all categories */
  async function handleSaveAll() {
    if (!hasAnyEdits) return
    const allEdits: Record<string, string> = {}
    for (const [key, edit] of Object.entries(edits)) {
      allEdits[key] = edit.value
    }

    const passwordChanged = 'AUTH_PASSWORD' in allEdits

    setSavingCats({ _all: true })
    setErrorMessage('')
    setNoticeMessage('')
    try {
      await updateSettings(allEdits)

      if (passwordChanged) {
        try { await logout() } catch { /* expected */ }
        window.location.href = '/'
        return
      }

      setEdits({})
      setNoticeMessage(t('adminSettings.saved'))
      await loadData()
    } catch (err) {
      // If password was changed, save may have succeeded but session is now invalid — redirect
      if (passwordChanged) {
        try { await logout() } catch { /* expected */ }
        window.location.href = '/'
        return
      }
      setErrorMessage(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setSavingCats({})
    }
  }

  async function handleReset(key: string) {
    try {
      await resetSettings([key])
      setNoticeMessage(t('adminSettings.resetDone', { key }))
      setEdits((prev) => { const n = { ...prev }; delete n[key]; return n })
      await loadData()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('common.error'))
    }
  }

  async function handleIbkrTest() {
    setIbkrTesting(true)
    setIbkrTestResult(null)
    try {
      setIbkrTestResult(await testIbkrConnection())
    } catch (err) {
      setIbkrTestResult({ success: false, message: err instanceof Error ? err.message : t('adminSettings.testFailed'), account_id: null })
    } finally {
      setIbkrTesting(false)
    }
  }

  async function handleLlmTest() {
    setLlmTesting(true)
    setLlmTestResult(null)
    try {
      setLlmTestResult(await testLlmProvider(llmTestPrompt))
    } catch (err) {
      setLlmTestResult({ success: false, model: null, content: null, latency_ms: null, message: err instanceof Error ? err.message : t('adminSettings.testFailed') })
    } finally {
      setLlmTesting(false)
    }
  }

  async function handleEmailSave() {
    setEmailSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const payload: Record<string, unknown> = {
        smtp_host: emailForm.smtp_host || null,
        smtp_port: emailForm.smtp_port,
        smtp_username: emailForm.smtp_username || null,
        from_address: emailForm.from_address || null,
        to_addresses: emailForm.to_addresses ? emailForm.to_addresses.split(',').map((s) => s.trim()).filter(Boolean) : [],
        enabled: emailForm.enabled,
      }
      if (emailForm.smtp_password) payload.smtp_password = emailForm.smtp_password
      const updated = await updateEmailSettings(payload)
      setEmailSettings(updated)
      setEmailForm((prev) => ({ ...prev, smtp_password: '' }))
      setNoticeMessage(t('adminSettings.emailSaved'))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setEmailSaving(false)
    }
  }

  async function handleEmailTest() {
    setEmailTesting(true)
    setEmailTestResult(null)
    try {
      setEmailTestResult(await sendEmailTest())
    } catch (err) {
      setEmailTestResult({ success: false, message: err instanceof Error ? err.message : t('adminSettings.testFailed') })
    } finally {
      setEmailTesting(false)
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  const categories = Object.keys(settings)

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('admin.title')}</p>
              <h2 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-text-bright)' }}>{t('admin.settings')}</h2>
              <p className="panel-subtitle">{t('adminSettings.subtitle')}</p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn--sm" onClick={() => { resetSettings(undefined).then(() => { setEdits({}); void loadData() }) }}>
                {t('adminSettings.resetAll')}
              </button>
              <button className="btn btn--sm btn--accent" onClick={handleSaveAll} disabled={!hasAnyEdits || !!savingCats._all}>
                {savingCats._all ? t('adminSettings.saving') : t('adminSettings.saveAll')}
              </button>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
          {errorMessage}
        </div>
      )}
      {noticeMessage && (
        <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(61,214,140,0.2)', background: 'rgba(61,214,140,0.05)', color: 'var(--color-positive)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
          {noticeMessage}
        </div>
      )}

      {/* Accordion categories from SETTINGS_SCHEMA */}
      {categories.map((cat) => {
        const items = settings[cat] || []
        const catLabel = t(`adminSettings.cat.${cat}`, { defaultValue: cat.toUpperCase() })
        const isExpanded = expanded === cat
        const catHasEdits = dirtyCategories.has(cat)
        const catSaving = !!savingCats[cat]

        return (
          <section key={cat} className="surface-panel">
            <div className="surface-panel__content" style={{ padding: '10px 14px' }}>
              <button
                onClick={() => toggle(cat)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--color-text-bright)', fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.06em',
                  textTransform: 'uppercase', padding: '4px 0',
                }}
              >
                <span>{catLabel}</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{isExpanded ? '▲' : '▼'}</span>
              </button>

              {isExpanded && (
                <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                  {items.map((item: SettingItem) => {
                    const edit = edits[item.key]
                    const displayVal = edit ? edit.value : item.value
                    const isEdited = edit !== undefined && edit.value !== item.value

                    return (
                      <div key={item.key} style={{
                        display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8, alignItems: 'center',
                        padding: '6px 8px', borderRadius: 'var(--radius-sm)',
                        background: isEdited ? 'rgba(88,166,255,0.04)' : 'transparent',
                        border: `1px solid ${isEdited ? 'rgba(88,166,255,0.2)' : 'transparent'}`,
                      }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>{t(`adminSettings.fields.${item.key}`, { defaultValue: item.label })}</div>
                          <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{item.key}</div>
                        </div>
                        <SettingField
                          item={item}
                          value={displayVal}
                          onChange={(v) => handleEdit(item.key, v, cat)}
                        />
                        <button
                          className="btn btn--ghost btn--sm"
                          onClick={() => handleReset(item.key)}
                          title={t('adminSettings.resetHint')}
                          style={{ minHeight: 26, padding: '0 6px', fontSize: '0.65rem' }}
                        >
                          {t('adminSettings.reset')}
                        </button>
                      </div>
                    )
                  })}

                  {/* Category action bar */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '6px 0 2px' }}>
                    {cat === 'ibkr' && (
                      <button className="btn btn--sm" onClick={handleIbkrTest} disabled={ibkrTesting}>
                        {ibkrTesting ? t('adminSettings.testing') : t('adminSettings.testIbkr')}
                      </button>
                    )}
                    {cat === 'llm' && (
                      <button className="btn btn--sm" onClick={handleLlmTest} disabled={llmTesting}>
                        {llmTesting ? t('adminSettings.testing') : t('adminSettings.testLlm')}
                      </button>
                    )}
                    <button className="btn btn--sm btn--accent" onClick={() => handleCategorySave(cat)} disabled={!catHasEdits || catSaving}>
                      {catSaving ? t('adminSettings.saving') : t('adminSettings.save')}
                    </button>
                  </div>

                  {/* IBKR Test Result */}
                  {cat === 'ibkr' && ibkrTestResult && (
                    <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: `1px solid ${ibkrTestResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: ibkrTestResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                      <span className={`tag ${ibkrTestResult.success ? 'tag--positive' : 'tag--negative'}`}>{ibkrTestResult.success ? t('adminSettings.success') : t('adminSettings.failed')}</span>
                      <p style={{ margin: '6px 0 0', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>{ibkrTestResult.message}</p>
                    </div>
                  )}

                  {/* LLM Test Panel */}
                  {cat === 'llm' && (
                    <>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                        <label className="field-stack" style={{ flex: 1 }}>
                          <span className="field-stack__label" style={{ fontSize: '0.7rem' }}>{t('adminSettings.testPrompt')}</span>
                          <input className="input" value={llmTestPrompt} onChange={(e) => setLlmTestPrompt(e.target.value)} placeholder="Say OK" style={{ minHeight: 28, fontSize: '0.78rem' }} />
                        </label>
                      </div>
                      {llmTestResult && (
                        <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: `1px solid ${llmTestResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: llmTestResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                          <div style={{ display: 'flex', gap: 10, marginBottom: 6 }}>
                            <span className={`tag ${llmTestResult.success ? 'tag--positive' : 'tag--negative'}`}>{llmTestResult.success ? t('adminSettings.success') : t('adminSettings.failed')}</span>
                            {llmTestResult.model && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{t('adminSettings.model')}: {llmTestResult.model}</span>}
                            {llmTestResult.latency_ms != null && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{llmTestResult.latency_ms}ms</span>}
                          </div>
                          <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                            {llmTestResult.content || llmTestResult.error || llmTestResult.message || t('adminSettings.noResponse')}
                          </pre>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </section>
        )
      })}

      {/* Email Settings */}
      <section className="surface-panel">
        <div className="surface-panel__content" style={{ padding: '10px 14px' }}>
          <button
            onClick={() => toggle('email')}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              width: '100%', background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--color-text-bright)', fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', padding: '4px 0',
            }}
          >
            <span>{t('adminSettings.cat.email')}</span>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{expanded === 'email' ? '▲' : '▼'}</span>
          </button>

          {expanded === 'email' && (
            <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
              {emailLoading ? (
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>{t('common.loading')}</div>
              ) : (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 6 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 8, alignItems: 'center', padding: '6px 8px' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>{t('adminSettings.smtpHost')}</div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>email_smtp_host</div>
                      </div>
                      <input className="input" value={emailForm.smtp_host} onChange={(e) => setEmailForm({ ...emailForm, smtp_host: e.target.value })} placeholder="smtp.gmail.com" style={{ minHeight: 28, fontSize: '0.78rem' }} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr', gap: 8, alignItems: 'center', padding: '6px 8px' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>{t('adminSettings.smtpPort')}</div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>email_smtp_port</div>
                      </div>
                      <input className="input" type="number" value={emailForm.smtp_port} onChange={(e) => setEmailForm({ ...emailForm, smtp_port: Number(e.target.value) })} style={{ minHeight: 28, fontSize: '0.78rem' }} />
                    </div>
                  </div>
                  {([
                    { label: t('adminSettings.smtpUsername'), key: 'smtp_username' as const, placeholder: 'your@email.com', type: 'text', dbKey: 'email_smtp_username' },
                    { label: t('adminSettings.smtpPassword'), key: 'smtp_password' as const, placeholder: emailSettings?.smtp_password_set ? '••••••••' : t('adminSettings.smtpPassword'), type: 'password', dbKey: 'email_smtp_password' },
                    { label: t('adminSettings.fromAddress'), key: 'from_address' as const, placeholder: 'noreply@example.com', type: 'text', dbKey: 'email_from_address' },
                    { label: t('adminSettings.toAddresses'), key: 'to_addresses' as const, placeholder: 'user1@example.com, user2@example.com', type: 'text', dbKey: 'email_to_addresses' },
                  ]).map((field) => (
                    <div key={field.key} style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 8, alignItems: 'center', padding: '6px 8px' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>
                          {field.label}
                          {field.key === 'smtp_password' && emailSettings?.smtp_password_set && (
                            <span style={{ marginLeft: 6, color: 'var(--color-positive)', fontSize: '0.65rem' }}>{t('adminSettings.passwordSet')}</span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{field.dbKey}</div>
                      </div>
                      <input
                        className="input"
                        type={field.type}
                        value={emailForm[field.key]}
                        onChange={(e) => setEmailForm({ ...emailForm, [field.key]: e.target.value })}
                        placeholder={field.placeholder}
                        style={{ minHeight: 28, fontSize: '0.78rem' }}
                      />
                    </div>
                  ))}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px' }}>
                    <input type="checkbox" checked={emailForm.enabled} onChange={(e) => setEmailForm({ ...emailForm, enabled: e.target.checked })} style={{ accentColor: 'var(--color-accent)' }} />
                    <span style={{ fontSize: '0.78rem' }}>{t('adminSettings.enableEmail')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '6px 0 2px' }}>
                    <button className="btn btn--sm" onClick={handleEmailTest} disabled={emailTesting}>
                      {emailTesting ? t('adminSettings.sending') : t('adminSettings.testEmail')}
                    </button>
                    <button className="btn btn--sm btn--accent" onClick={handleEmailSave} disabled={emailSaving}>
                      {emailSaving ? t('adminSettings.saving') : t('adminSettings.save')}
                    </button>
                  </div>
                  {emailTestResult && (
                    <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: `1px solid ${emailTestResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: emailTestResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                      <span className={`tag ${emailTestResult.success ? 'tag--positive' : 'tag--negative'}`}>{emailTestResult.success ? t('adminSettings.sent') : t('adminSettings.failed')}</span>
                      <span style={{ marginLeft: 8, fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>{emailTestResult.message}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </section>
    </section>
  )
}

/* ---------- field renderer ---------- */

function SettingField({ item, value, onChange }: { item: SettingItem; value: string; onChange: (v: string) => void }) {
  // Boolean → toggle switch
  if (item.type === 'boolean') {
    const checked = value === 'true' || value === '1'
    return (
      <div
        style={{ ...switchStyle, background: checked ? 'var(--color-accent)' : 'var(--color-border-subtle)' }}
        onClick={() => onChange(checked ? 'false' : 'true')}
        role="switch"
        aria-checked={checked}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); onChange(checked ? 'false' : 'true') } }}
      >
        <div style={{ ...switchKnob, left: checked ? 18 : 2 }} />
      </div>
    )
  }

  // Select → dropdown
  if (item.type === 'select' && item.options?.length) {
    return (
      <select
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ minHeight: 28, fontSize: '0.78rem' }}
      >
        {item.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    )
  }

  // Password → show value as text (admin page, already authenticated)
  if (item.type === 'password') {
    return (
      <input
        className="input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={item.default || ''}
        style={{ minHeight: 28, fontSize: '0.78rem' }}
      />
    )
  }

  // Default text / number
  return (
    <input
      className="input"
      type={item.type === 'number' ? 'number' : 'text'}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={item.default || ''}
      style={{ minHeight: 28, fontSize: '0.78rem' }}
    />
  )
}
