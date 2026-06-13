import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchIbkrSettings, updateIbkrSettings, testIbkrConnection } from '@/api/adminIbkr'
import AdminTabs from '@/components/AdminTabs'
import type { IbkrSettings, IbkrTestResponse } from '@/types/adminIbkr'

export default function AdminIbkrView() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<IbkrSettings | null>(null)
  const [testResult, setTestResult] = useState<IbkrTestResponse | null>(null)
  const [flexToken, setFlexToken] = useState('')
  const [queryId, setQueryId] = useState('')
  const [queryIds, setQueryIds] = useState('')
  const [accountId, setAccountId] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const s = await fetchIbkrSettings()
      setSettings(s)
      setQueryId(s.flex_query_id ?? '')
      setQueryIds(s.flex_query_ids ?? '1532356,1532359')
      setAccountId(s.account_id ?? '')
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('adminIbkr.failedToLoad'))
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
      const payload: Record<string, string | null> = {}
      if (flexToken) payload.flex_token = flexToken
      if (queryId) payload.flex_query_id = queryId
      if (queryIds) payload.flex_query_ids = queryIds
      if (accountId) payload.account_id = accountId
      const updated = await updateIbkrSettings(payload)
      setSettings(updated)
      setFlexToken('')
      setNoticeMessage(t('adminIbkr.settingsSaved'))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('adminIbkr.failedToSave'))
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      setTestResult(await testIbkrConnection())
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : t('adminIbkr.testFailed'), account_id: null })
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
              <p className="eyebrow">{t('adminIbkr.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminIbkr.title')}</h2>
              <p className="panel-subtitle">{t('adminIbkr.subtitle')}</p>
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

      {/* Current Settings */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminIbkr.currentSettings')}</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
            {[
              { label: t('adminIbkr.flexToken'), value: settings?.flex_token ? '••••••••' : t('adminIbkr.notSet') },
              { label: t('adminIbkr.queryId'), value: settings?.flex_query_id || t('adminIbkr.notSet') },
              { label: t('adminIbkr.accountId'), value: settings?.account_id || t('adminIbkr.notSet') },
            ].map((item) => (
              <div key={item.label} style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', background: 'rgba(10,14,26,0.4)' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>{item.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--color-text-bright)' }}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Update Settings */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminIbkr.updateSettings')}</p>
          <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminIbkr.flexToken')} ({t('adminIbkr.keepCurrent')})</span>
              <input className="input" type="password" value={flexToken} onChange={(e) => setFlexToken(e.target.value)} placeholder={t('adminIbkr.flexTokenPlaceholder')} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminIbkr.flexQueryId')}</span>
              <input className="input" value={queryId} onChange={(e) => setQueryId(e.target.value)} placeholder="e.g. 1532356" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminIbkr.flexQueryIds')}</span>
              <input className="input" value={queryIds} onChange={(e) => setQueryIds(e.target.value)} placeholder="1532356,1532359" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('adminIbkr.accountId')}</span>
              <input className="input" value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="e.g. U1234567" />
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn btn--accent" onClick={handleSave} disabled={saving}>
                {saving ? t('adminIbkr.saving') : t('adminIbkr.saveSettings')}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Test Connection */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminIbkr.testConnection')}</p>
          <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
            <button className="btn" onClick={handleTest} disabled={testing} style={{ justifySelf: 'start' }}>
              {testing ? t('adminIbkr.testing') : t('adminIbkr.testBtn')}
            </button>
            {testResult && (
              <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: `1px solid ${testResult.success ? 'rgba(61,214,140,0.2)' : 'rgba(242,92,92,0.2)'}`, background: testResult.success ? 'rgba(61,214,140,0.05)' : 'rgba(242,92,92,0.05)' }}>
                <span className={`tag ${testResult.success ? 'tag--positive' : 'tag--negative'}`}>{testResult.success ? t('adminIbkr.success') : t('adminIbkr.failed')}</span>
                <p style={{ margin: '8px 0 0', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>{testResult.message}</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </section>
  )
}
