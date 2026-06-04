import { useState, useEffect, useCallback } from 'react'
import { fetchEmailSettings, sendEmailTest, sendLatestAccountSnapshot, sendLatestDailyReview, updateEmailSettings } from '@/api/adminEmail'
import AdminTabs from '@/components/AdminTabs'
import type { EmailSendLatestResponse, EmailSettings, EmailTestResponse } from '@/types/adminEmail'

export default function AdminEmailView() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [sendingReview, setSendingReview] = useState(false)
  const [sendingSnapshot, setSendingSnapshot] = useState(false)
  const [forceRefreshDailyReview, setForceRefreshDailyReview] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<EmailSettings | null>(null)
  const [testResult, setTestResult] = useState<EmailTestResponse | null>(null)
  const [reviewSendResult, setReviewSendResult] = useState<EmailSendLatestResponse | null>(null)
  const [snapshotSendResult, setSnapshotSendResult] = useState<EmailSendLatestResponse | null>(null)

  const [form, setForm] = useState({
    smtp_host: '', smtp_port: '465', smtp_username: '', smtp_password: '',
    smtp_use_ssl: true, smtp_use_starttls: false, email_from: '',
    daily_review_email_enabled: false, daily_review_email_to: '', daily_review_subject_prefix: 'IBKR Daily Review',
    site_base_url: '', daily_snapshot_email_enabled: false, daily_snapshot_email_to: '', daily_snapshot_subject_prefix: 'IBKR Daily Snapshot',
  })

  function applySettings(value: EmailSettings): void {
    setSettings(value)
    setForm({
      smtp_host: value.smtp_host, smtp_port: String(value.smtp_port), smtp_username: value.smtp_username,
      smtp_password: '', smtp_use_ssl: value.smtp_use_ssl, smtp_use_starttls: value.smtp_use_starttls,
      email_from: value.email_from, daily_review_email_enabled: value.daily_review_email_enabled,
      daily_review_email_to: value.daily_review_email_to, daily_review_subject_prefix: value.daily_review_subject_prefix,
      site_base_url: value.site_base_url || '', daily_snapshot_email_enabled: value.daily_snapshot_email_enabled,
      daily_snapshot_email_to: value.daily_snapshot_email_to, daily_snapshot_subject_prefix: value.daily_snapshot_subject_prefix,
    })
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try { applySettings(await fetchEmailSettings()) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Failed to load') }
    finally { setLoading(false) }
  }, [])

  async function saveSettings(): Promise<void> {
    setSaving(true); setErrorMessage(''); setNoticeMessage(''); setTestResult(null)
    try {
      const response = await updateEmailSettings({
        smtp_host: form.smtp_host.trim(), smtp_port: Number(form.smtp_port), smtp_username: form.smtp_username.trim(),
        smtp_password: form.smtp_password.trim() || undefined, smtp_use_ssl: form.smtp_use_ssl, smtp_use_starttls: form.smtp_use_starttls,
        email_from: form.email_from.trim(), daily_review_email_enabled: form.daily_review_email_enabled,
        daily_review_email_to: form.daily_review_email_to.trim(), daily_review_subject_prefix: form.daily_review_subject_prefix.trim(),
        site_base_url: form.site_base_url.trim(), daily_snapshot_email_enabled: form.daily_snapshot_email_enabled,
        daily_snapshot_email_to: form.daily_snapshot_email_to.trim(), daily_snapshot_subject_prefix: form.daily_snapshot_subject_prefix.trim(),
      })
      applySettings(response.settings); setNoticeMessage(response.message)
    } catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Failed to save') }
    finally { setSaving(false) }
  }

  async function runTest(): Promise<void> {
    setTesting(true); setErrorMessage(''); setNoticeMessage(''); setTestResult(null)
    try { const r = await sendEmailTest(); setTestResult(r); setNoticeMessage(r.message) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Test failed') }
    finally { setTesting(false) }
  }

  async function runSendReview(): Promise<void> {
    setSendingReview(true); setErrorMessage(''); setReviewSendResult(null)
    try { setReviewSendResult(await sendLatestDailyReview({ force_refresh: forceRefreshDailyReview })) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Send failed') }
    finally { setSendingReview(false) }
  }

  async function runSendSnapshot(): Promise<void> {
    setSendingSnapshot(true); setErrorMessage(''); setSnapshotSendResult(null)
    try { setSnapshotSendResult(await sendLatestAccountSnapshot()) }
    catch (error) { setErrorMessage(error instanceof Error ? error.message : 'Send failed') }
    finally { setSendingSnapshot(false) }
  }

  function updateForm(field: string, value: string | boolean): void { setForm((prev) => ({ ...prev, [field]: value })) }
  function normalizeTls(mode: 'ssl' | 'starttls'): void {
    if (mode === 'ssl' && form.smtp_use_ssl) setForm((p) => ({ ...p, smtp_use_starttls: false }))
    if (mode === 'starttls' && form.smtp_use_starttls) setForm((p) => ({ ...p, smtp_use_ssl: false }))
  }

  useEffect(() => { void loadData() }, [loadData])

  const inputStyle: React.CSSProperties = { width: '100%', border: '1px solid rgba(129, 160, 207, 0.16)', borderRadius: 12, background: 'rgba(10, 18, 32, 0.85)', color: 'var(--color-text-primary)', outline: 'none', minHeight: 44, padding: '0.8rem 0.95rem' }
  const metaBox: React.CSSProperties = { padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Email Configuration</h2>
              <p className="panel-subtitle">SMTP configuration for daily review and account snapshot emails.</p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: settings?.daily_review_email_enabled ? 'rgba(52, 210, 163, 0.15)' : 'rgba(129, 160, 207, 0.1)', color: settings?.daily_review_email_enabled ? 'var(--color-positive)' : 'var(--color-text-secondary)' }}>{settings?.daily_review_email_enabled ? 'DAILY REVIEW ON' : 'DAILY REVIEW OFF'}</span>
              <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', fontWeight: 600, background: settings?.daily_snapshot_email_enabled ? 'rgba(52, 210, 163, 0.15)' : 'rgba(129, 160, 207, 0.1)', color: settings?.daily_snapshot_email_enabled ? 'var(--color-positive)' : 'var(--color-text-secondary)' }}>{settings?.daily_snapshot_email_enabled ? 'SNAPSHOT ON' : 'SNAPSHOT OFF'}</span>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section> : (
        <>
          {noticeMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-positive)', background: 'rgba(9, 47, 39, 0.48)', border: '1px solid rgba(52, 210, 163, 0.18)' }}>{noticeMessage}</p>}
          {errorMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-negative)', background: 'rgba(55, 18, 28, 0.48)', border: '1px solid rgba(255, 107, 122, 0.18)' }}>{errorMessage}</p>}

          <section className="surface-panel">
            <div className="surface-panel__content">
              <h3 className="panel-title">SMTP Configuration</h3>
              <p className="panel-subtitle">Shared SMTP settings for all email types.</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                <label className="field-stack"><span className="field-stack__label">SMTP Host</span><input style={inputStyle} value={form.smtp_host} onChange={(e) => updateForm('smtp_host', e.target.value)} placeholder="smtp.example.com" /></label>
                <label className="field-stack"><span className="field-stack__label">SMTP Port</span><input style={inputStyle} type="number" min={1} max={65535} value={form.smtp_port} onChange={(e) => updateForm('smtp_port', e.target.value)} /></label>
                <label className="field-stack"><span className="field-stack__label">SMTP Username</span><input style={inputStyle} value={form.smtp_username} onChange={(e) => updateForm('smtp_username', e.target.value)} /></label>
                <label className="field-stack"><span className="field-stack__label">SMTP Password</span><input style={inputStyle} type="password" value={form.smtp_password} onChange={(e) => updateForm('smtp_password', e.target.value)} placeholder={settings?.has_smtp_password ? `Saved: ${settings.smtp_password_masked}` : 'SMTP password / auth code'} /></label>
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 'var(--space-3)' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}><input type="checkbox" checked={form.smtp_use_ssl} onChange={() => { updateForm('smtp_use_ssl', !form.smtp_use_ssl); if (!form.smtp_use_ssl) normalizeTls('ssl') }} style={{ accentColor: 'var(--color-accent)' }} /><span>SSL</span></label>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}><input type="checkbox" checked={form.smtp_use_starttls} onChange={() => { updateForm('smtp_use_starttls', !form.smtp_use_starttls); if (!form.smtp_use_starttls) normalizeTls('starttls') }} style={{ accentColor: 'var(--color-accent)' }} /><span>STARTTLS</span></label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
                <label className="field-stack"><span className="field-stack__label">Email From</span><input style={inputStyle} value={form.email_from} onChange={(e) => updateForm('email_from', e.target.value)} placeholder="IBKR Show &lt;name@example.com&gt;" /></label>
                <label className="field-stack"><span className="field-stack__label">Site Base URL</span><input style={inputStyle} value={form.site_base_url} onChange={(e) => updateForm('site_base_url', e.target.value)} placeholder="https://example.com" /></label>
              </div>
              <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', margin: 'var(--space-3) 0 0' }}>
                <div style={metaBox}><dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Password Status</dt><dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{settings?.smtp_password_masked || '--'}</dd></div>
                <div style={metaBox}><dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Config File</dt><dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{settings?.config_file || '--'}</dd></div>
              </dl>
            </div>
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div><h3 className="panel-title">Daily Review Email</h3><p className="panel-subtitle">Sent after daily position review generation.</p></div>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}><input type="checkbox" checked={form.daily_review_email_enabled} onChange={() => updateForm('daily_review_email_enabled', !form.daily_review_email_enabled)} style={{ accentColor: 'var(--color-accent)' }} /><span>Enabled</span></label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                <label className="field-stack"><span className="field-stack__label">Recipients</span><input style={inputStyle} value={form.daily_review_email_to} onChange={(e) => updateForm('daily_review_email_to', e.target.value)} placeholder="me@example.com, other@example.com" /></label>
                <label className="field-stack"><span className="field-stack__label">Subject Prefix</span><input style={inputStyle} value={form.daily_review_subject_prefix} onChange={(e) => updateForm('daily_review_subject_prefix', e.target.value)} /></label>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginTop: 'var(--space-3)', flexWrap: 'wrap' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}><input type="checkbox" checked={forceRefreshDailyReview} onChange={() => setForceRefreshDailyReview(!forceRefreshDailyReview)} style={{ accentColor: 'var(--color-accent)' }} /><span>Force regenerate</span></label>
                <button className="btn btn--accent" style={{ minWidth: 280, height: 44 }} disabled={!form.daily_review_email_enabled || !form.daily_review_email_to.trim() || sendingReview} onClick={() => void runSendReview()}>{sendingReview ? 'Sending...' : 'Send Latest Daily Review'}</button>
                {reviewSendResult && <span style={{ color: reviewSendResult.success ? 'var(--color-positive)' : 'var(--color-negative)', fontSize: '0.82rem' }}>{reviewSendResult.message}{reviewSendResult.report_date ? ` (${reviewSendResult.report_date})` : ''}</span>}
              </div>
            </div>
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div><h3 className="panel-title">Account Snapshot Email</h3><p className="panel-subtitle">Sends account snapshot to Gmail for ChatGPT connector.</p></div>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}><input type="checkbox" checked={form.daily_snapshot_email_enabled} onChange={() => updateForm('daily_snapshot_email_enabled', !form.daily_snapshot_email_enabled)} style={{ accentColor: 'var(--color-accent)' }} /><span>Enabled</span></label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                <label className="field-stack"><span className="field-stack__label">Gmail Recipient</span><input style={inputStyle} value={form.daily_snapshot_email_to} onChange={(e) => updateForm('daily_snapshot_email_to', e.target.value)} placeholder="gmail@example.com" /></label>
                <label className="field-stack"><span className="field-stack__label">Subject Prefix</span><input style={inputStyle} value={form.daily_snapshot_subject_prefix} onChange={(e) => updateForm('daily_snapshot_subject_prefix', e.target.value)} /></label>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginTop: 'var(--space-3)', flexWrap: 'wrap' }}>
                <button className="btn btn--accent" style={{ minWidth: 280, height: 44 }} disabled={!form.daily_snapshot_email_enabled || !form.daily_snapshot_email_to.trim() || sendingSnapshot} onClick={() => void runSendSnapshot()}>{sendingSnapshot ? 'Sending...' : 'Send Latest Account Snapshot'}</button>
                {snapshotSendResult && <span style={{ color: snapshotSendResult.success ? 'var(--color-positive)' : 'var(--color-negative)', fontSize: '0.82rem' }}>{snapshotSendResult.message}{snapshotSendResult.report_date ? ` (${snapshotSendResult.report_date})` : ''}</span>}
              </div>
            </div>
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <h3 className="panel-title">Status</h3>
              <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}><span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Daily Review Recipients</span><strong>{settings?.daily_review_email_to || '--'}</strong></div>
                <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}><span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Snapshot Recipients</span><strong>{settings?.daily_snapshot_email_to || '--'}</strong></div>
                {testResult && <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: testResult.success ? 'rgba(9, 47, 39, 0.42)' : 'rgba(55, 18, 28, 0.5)', border: `1px solid ${testResult.success ? 'rgba(52, 210, 163, 0.18)' : 'rgba(255, 107, 125, 0.2)'}` }}><span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Test Email</span><strong>{testResult.success ? 'Sent' : 'Failed'}</strong><p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>{testResult.sent_to.join(', ')}</p></div>}
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 'var(--space-3)' }}>
                <button className="btn btn--accent" disabled={saving} onClick={() => void saveSettings()}>{saving ? 'Saving...' : 'Save Config'}</button>
                <button className="btn btn--ghost" disabled={testing} onClick={() => void runTest()}>{testing ? 'Sending...' : 'Send Test Email'}</button>
              </div>
            </div>
          </section>
        </>
      )}
    </section>
  )
}
