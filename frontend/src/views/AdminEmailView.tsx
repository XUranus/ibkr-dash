import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchEmailSettings, updateEmailSettings, sendEmailTest } from '@/api/adminEmail'
import AdminTabs from '@/components/AdminTabs'
import type { EmailSettings, EmailTestResponse } from '@/types/adminEmail'

export default function AdminEmailView() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<EmailSettings | null>(null)
  const [testResult, setTestResult] = useState<EmailTestResponse | null>(null)

  const [form, setForm] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_address: '',
    to_addresses: '',
    enabled: false,
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const s = await fetchEmailSettings()
      setSettings(s)
      setForm({
        smtp_host: s.smtp_host ?? '',
        smtp_port: s.smtp_port ?? 587,
        smtp_username: s.smtp_username ?? '',
        smtp_password: '',
        from_address: s.from_address ?? '',
        to_addresses: s.to_addresses?.join(', ') ?? '',
        enabled: s.enabled,
      })
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('adminEmail.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  async function handleSave() {
    setSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      const payload: Record<string, unknown> = {
        smtp_host: form.smtp_host || null,
        smtp_port: form.smtp_port,
        smtp_username: form.smtp_username || null,
        from_address: form.from_address || null,
        to_addresses: form.to_addresses ? form.to_addresses.split(',').map((s) => s.trim()).filter(Boolean) : [],
        enabled: form.enabled,
      }
      if (form.smtp_password) payload.smtp_password = form.smtp_password
      const updated = await updateEmailSettings(payload)
      setSettings(updated)
      setForm((prev) => ({ ...prev, smtp_password: '' }))
      setNoticeMessage(t('adminEmail.emailSettingsSaved'))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('adminEmail.failedToSave'))
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      setTestResult(await sendEmailTest())
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : t('adminEmail.testFailed') })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminEmail.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminEmail.title')}</h2>
              <p className="panel-subtitle">{t('adminEmail.subtitle')}</p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}
      {noticeMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(61,214,140,0.2)', background: 'rgba(61,214,140,0.05)', color: 'var(--color-positive)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {noticeMessage}
        </div>
      )}

      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminEmail.smtpSettings')}</p>
          <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12 }}>
              <label className="field-stack">
                <span className="field-stack__label">{t('adminEmail.smtpHost')}</span>
                <input className="input" value={form.smtp_host} onChange={(e) => setForm({ ...form, smtp_host: e.target.value })} placeholder="smtp.gmail.com" />
              </label>
              <label className="field-stack">
                <span className="field-stack__label">{t('adminEmail.port')}</span>
                <input className="input" type="number" value={form.smtp_port} onChange={(e) => setForm({ ...form, smtp_port: Number(e.target.value) })} />
              </label>
            </div>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminEmail.username')}</span>
              <input className="input" value={form.smtp_username} onChange={(e) => setForm({ ...form, smtp_username: e.target.value })} placeholder="your@email.com" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminEmail.password')} {settings?.smtp_password_set && <span style={{ color: 'var(--color-positive)' }}>{t('adminEmail.set')}</span>}</span>
              <input className="input" type="password" value={form.smtp_password} onChange={(e) => setForm({ ...form, smtp_password: e.target.value })} placeholder={settings?.smtp_password_set ? '••••••••' : t('adminEmail.password')} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminEmail.fromAddress')}</span>
              <input className="input" value={form.from_address} onChange={(e) => setForm({ ...form, from_address: e.target.value })} placeholder="noreply@example.com" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminEmail.toAddresses')}</span>
              <input className="input" value={form.to_addresses} onChange={(e) => setForm({ ...form, to_addresses: e.target.value })} placeholder="user1@example.com, user2@example.com" />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} style={{ accentColor: 'var(--color-accent)' }} />
              <span style={{ fontSize: '0.88rem' }}>{t('adminEmail.enableEmail')}</span>
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn" onClick={handleTest} disabled={testing}>
                {testing ? t('adminEmail.sending') : t('adminEmail.sendTest')}
              </button>
              <button className="btn btn--accent" onClick={handleSave} disabled={saving}>
                {saving ? t('adminEmail.saving') : t('adminEmail.save')}
              </button>
            </div>
          </div>
          {testResult && (
            <div style={{ marginTop: 12, padding: '12px 16px', borderRadius: 'var(--radius-md)', border: `1px solid ${testResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: testResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
              <span className={`tag ${testResult.success ? 'tag--positive' : 'tag--negative'}`}>{testResult.success ? t('adminEmail.sent') : t('adminEmail.failed')}</span>
              <span style={{ marginLeft: 8, fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>{testResult.message}</span>
            </div>
          )}
        </div>
      </section>
    </section>
  )
}
