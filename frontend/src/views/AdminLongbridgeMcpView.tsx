import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import AdminTabs from '@/components/AdminTabs'
import { fetchSystemStatus } from '@/api/adminSystem'
import { testLongbridgeConnection } from '@/api/adminLongbridge'
import type { AdminSystemStatus } from '@/types/adminSystem'
import type { LongbridgeMcpTestResponse } from '@/types/adminLongbridgeMcp'

export default function AdminLongbridgeMcpView() {
  const { t } = useTranslation()
  const [status, setStatus] = useState<AdminSystemStatus | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<LongbridgeMcpTestResponse | null>(null)
  const [testError, setTestError] = useState('')

  useEffect(() => {
    fetchSystemStatus().then(setStatus).catch(() => {})
  }, [])

  const handleTest = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    setTestError('')
    try {
      const result = await testLongbridgeConnection()
      setTestResult(result)
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setTesting(false)
    }
  }, [])

  const lb = status?.longbridge
  const isConfigured = lb?.configured ?? false

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminLongbridge.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminLongbridge.title')}</h2>
              <p className="panel-subtitle">{t('adminLongbridge.subtitle')}</p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {/* Config status */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminLongbridge.status')}</p>
          <div style={{ marginTop: 12 }}>
            <span className={`tag ${isConfigured ? 'tag--positive' : 'tag--warning'}`}>
              {isConfigured ? t('adminSystem.configured') : t('adminLongbridge.notConfigured')}
            </span>

            {lb && (
              <div style={{ marginTop: 16, display: 'grid', gap: 6 }}>
                <Row label="App Key" value={lb.app_key_configured ? '✓' : '—'} ok={lb.app_key_configured} />
                <Row label="App Secret" value={lb.app_secret_configured ? '✓' : '—'} ok={lb.app_secret_configured} />
                <Row label="Access Token" value={lb.access_token_configured ? '✓' : '—'} ok={lb.access_token_configured} />
                <Row label="SDK" value={lb.sdk_installed ? (lb.sdk_version ? `longport ${lb.sdk_version}` : 'longport ✓') : 'Not Installed'} ok={lb.sdk_installed} />
              </div>
            )}

            {!isConfigured && (
              <>
                <p style={{ marginTop: 12, color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                  {t('adminLongbridge.notConfiguredDesc')}
                </p>
                <pre style={{ marginTop: 12, padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.6)', border: '1px solid var(--color-border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', overflow: 'auto' }}>
{`LONGBRIDGE_APP_KEY=your-app-key
LONGBRIDGE_APP_SECRET=your-app-secret
LONGBRIDGE_ACCESS_TOKEN=your-access-token`}
                </pre>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Test connection */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminSystem.connectivity')}</p>
          <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              className="btn btn--primary"
              onClick={handleTest}
              disabled={testing || !isConfigured}
              style={{ minWidth: 140 }}
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            {lb && (
              <span className={`tag ${
                lb.connectivity === 'ok' ? 'tag--positive' :
                lb.connectivity === 'error' ? 'tag--negative' :
                lb.connectivity === 'degraded' ? 'tag--warning' :
                'tag--warning'
              }`}>
                {lb.connectivity === 'ok' ? 'Connected' :
                 lb.connectivity === 'error' ? 'Failed' :
                 lb.connectivity === 'degraded' ? 'Degraded' :
                 '—'}
              </span>
            )}
          </div>

          {/* Test result */}
          {testResult && (
            <div style={{
              marginTop: 16,
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              border: `1px solid ${testResult.success ? 'rgba(46,160,67,0.3)' : 'rgba(242,92,92,0.3)'}`,
              background: testResult.success ? 'rgba(46,160,67,0.05)' : 'rgba(242,92,92,0.05)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: testResult.quote_sample ? 12 : 0 }}>
                <span style={{ color: testResult.success ? 'var(--color-positive)' : 'var(--color-negative)', fontWeight: 600 }}>
                  {testResult.success ? '✓' : '✗'}
                </span>
                <span style={{ color: 'var(--color-text-bright)', fontSize: '0.9rem' }}>
                  {testResult.message}
                </span>
              </div>
              {testResult.quote_sample && (
                <div style={{ display: 'grid', gap: 4 }}>
                  <Row label="Symbol" value={String(testResult.quote_sample.symbol)} />
                  <Row label="Last Price" value={String(testResult.quote_sample.last_done)} />
                  <Row label="Prev Close" value={String(testResult.quote_sample.prev_close)} />
                  <Row label="Volume" value={Number(testResult.quote_sample.volume).toLocaleString()} />
                  <Row label="Turnover" value={String(testResult.quote_sample.turnover)} />
                </div>
              )}
            </div>
          )}
          {testError && (
            <div style={{ marginTop: 16, padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.3)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontSize: '0.9rem' }}>
              ✗ {testError}
            </div>
          )}
        </div>
      </section>
    </section>
  )
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(10,14,26,0.4)', marginBottom: 4 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.82rem',
        color: ok === true ? 'var(--color-positive)' : ok === false ? 'var(--color-negative)' : 'var(--color-text-bright)',
      }}>{value}</span>
    </div>
  )
}
