import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchIbkrSettings, importIbkrHistory, pullDailyFromIbkr, testIbkrConnection, updateIbkrSettings } from '@/api/adminIbkr'
import AdminTabs from '@/components/AdminTabs'
import type { IbkrFlexSettings, IbkrFlexTestResponse, IbkrImportResponse } from '@/types/adminIbkr'

export default function AdminIbkrView() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [pulling, setPulling] = useState(false)
  const [importing, setImporting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<IbkrFlexSettings | null>(null)
  const [testResult, setTestResult] = useState<IbkrFlexTestResponse | null>(null)
  const [importResult, setImportResult] = useState<IbkrImportResponse | null>(null)
  const [queryId, setQueryId] = useState('')
  const [flexToken, setFlexToken] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [selectedFileName, setSelectedFileName] = useState('')
  const [selectedFileSize, setSelectedFileSize] = useState(0)
  const selectedFileRef = useRef<File | null>(null)

  function applySettings(value: IbkrFlexSettings): void {
    setSettings(value)
    setQueryId(value.query_id)
    setFlexToken('')
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      applySettings(await fetchIbkrSettings())
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load IBKR settings')
    } finally {
      setLoading(false)
    }
  }, [])

  async function saveSettings(): Promise<void> {
    setSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    setTestResult(null)
    try {
      const response = await updateIbkrSettings({ query_id: queryId.trim(), flex_token: flexToken.trim() || undefined })
      applySettings(response.settings)
      setNoticeMessage(response.message)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function runTest(): Promise<void> {
    setTesting(true)
    setErrorMessage('')
    setNoticeMessage('')
    setTestResult(null)
    try {
      setTestResult(await testIbkrConnection())
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Test failed')
    } finally {
      setTesting(false)
    }
  }

  async function runPull(): Promise<void> {
    setPulling(true)
    setErrorMessage('')
    setNoticeMessage('')
    setImportResult(null)
    try {
      const result = await pullDailyFromIbkr()
      setImportResult(result)
      setNoticeMessage(result.message)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Pull failed')
    } finally {
      setPulling(false)
    }
  }

  async function runImport(): Promise<void> {
    const file = selectedFileRef.current
    if (!file) { setErrorMessage('Please select a CSV file first'); return }
    setImporting(true)
    setErrorMessage('')
    setNoticeMessage('')
    setImportResult(null)
    try {
      const result = await importIbkrHistory(file)
      setImportResult(result)
      setNoticeMessage(result.message)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0] ?? null
    selectedFileRef.current = file
    setSelectedFileName(file?.name ?? '')
    setSelectedFileSize(file?.size ?? 0)
    setImportResult(null)
  }

  useEffect(() => { void loadData() }, [loadData])

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">ADMIN</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>IBKR Data Source</h2>
              <p className="panel-subtitle">Configure Flex Web Service and import IBKR historical data.</p>
            </div>
            <span style={{ padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', fontWeight: 600, background: settings?.has_flex_token ? 'rgba(52, 210, 163, 0.15)' : 'rgba(255, 107, 122, 0.15)', color: settings?.has_flex_token ? 'var(--color-positive)' : 'var(--color-negative)' }}>{settings?.has_flex_token ? 'TOKEN SAVED' : 'TOKEN MISSING'}</span>
          </div>
          <AdminTabs />
        </div>
      </section>

      {loading ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state">Loading...</div></div></section>
      ) : errorMessage ? (
        <section className="surface-panel"><div className="surface-panel__content"><div className="empty-state" style={{ color: 'var(--color-negative)' }}>{errorMessage}</div></div></section>
      ) : (
        <>
          {noticeMessage && <p style={{ margin: 0, padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--color-positive)', background: 'rgba(9, 47, 39, 0.48)', border: '1px solid rgba(52, 210, 163, 0.18)' }}>{noticeMessage}</p>}

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(360px, 0.85fr)', gap: 'var(--space-4)' }}>
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Flex Configuration</h3>
                <p className="panel-subtitle">Query ID and FLEX_TOKEN are saved to the backend config file.</p>
                <form style={{ display: 'grid', gap: 'var(--space-3)' }} onSubmit={(e) => { e.preventDefault(); void saveSettings() }}>
                  <label className="field-stack"><span className="field-stack__label">Query ID</span><input className="input" value={queryId} onChange={(e) => setQueryId(e.target.value)} required placeholder="e.g. 1419985" /></label>
                  <label className="field-stack"><span className="field-stack__label">FLEX_TOKEN</span><input className="input" type="password" value={flexToken} onChange={(e) => setFlexToken(e.target.value)} placeholder={settings?.has_flex_token ? `Saved: ${settings.flex_token_masked}, leave empty to keep` : 'Get from IBKR Flex Web Service'} /></label>
                  <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 'var(--space-3)', margin: 0 }}>
                    <div style={{ padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}>
                      <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Current Query ID</dt>
                      <dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{settings?.query_id || '--'}</dd>
                    </div>
                    <div style={{ padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}>
                      <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Token</dt>
                      <dd style={{ margin: '6px 0 0', overflowWrap: 'anywhere', fontWeight: 600 }}>{settings?.flex_token_masked || '--'}</dd>
                    </div>
                  </dl>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
                    <button type="submit" className="btn btn--accent" disabled={saving}>{saving ? 'Saving...' : 'Save Config'}</button>
                    <button type="button" className="btn btn--ghost" disabled={testing} onClick={() => void runTest()}>{testing ? 'Testing...' : 'Test Connection'}</button>
                  </div>
                </form>
              </div>
            </section>

            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Historical Data Import</h3>
                <p className="panel-subtitle">Upload IBKR Flex CSV for the backend to import.</p>
                <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                  <label style={{ position: 'relative', display: 'grid', justifyItems: 'center', gap: 10, minHeight: 190, padding: 28, border: '1px dashed rgba(129, 160, 207, 0.28)', borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.48)', color: 'var(--color-text-primary)', cursor: 'pointer' }}>
                    <input ref={fileInputRef} type="file" accept=".csv,text/csv,text/plain" onChange={handleFileChange} style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }} />
                    <strong>{selectedFileName || 'Select a CSV file'}</strong>
                    {selectedFileName && <small style={{ color: 'var(--color-text-secondary)' }}>{(selectedFileSize / 1024).toFixed(1)} KB</small>}
                  </label>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
                    <button className="btn btn--accent" disabled={!selectedFileName || importing} onClick={() => void runImport()}>{importing ? 'Importing...' : 'Import History'}</button>
                    <button className="btn btn--ghost" disabled={pulling} onClick={() => void runPull()}>{pulling ? 'Pulling...' : 'Pull Latest from IBKR'}</button>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {(testResult || importResult) && (
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="panel-title">Results</h3>
                {testResult && (
                  <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: testResult.success ? 'rgba(9, 47, 39, 0.42)' : 'rgba(55, 18, 28, 0.5)', border: `1px solid ${testResult.success ? 'rgba(52, 210, 163, 0.18)' : 'rgba(255, 107, 125, 0.2)'}` }}>
                    <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Connection Test</span>
                    <strong>{testResult.success ? 'Success' : 'Failed'}</strong>
                    <p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>{testResult.message || testResult.reference_code}</p>
                  </div>
                )}
                {importResult && (
                  <div style={{ display: 'grid', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
                    <div style={{ display: 'grid', gap: 8, padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(10, 18, 32, 0.52)', border: '1px solid rgba(129, 160, 207, 0.12)' }}>
                      <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>File</span>
                      <strong>{importResult.filename}</strong>
                      <p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>{importResult.message}</p>
                    </div>
                    <div className="table-shell" style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', minWidth: 520, borderCollapse: 'collapse' }}>
                        <thead><tr>{['Index', 'Upserted'].map((h) => <th key={h} style={{ padding: '0.9rem 1rem', borderBottom: '1px solid rgba(129, 160, 207, 0.12)', textAlign: 'left', color: 'var(--color-text-secondary)', fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{h}</th>)}</tr></thead>
                        <tbody>
                          {Object.values(importResult.result).map((row) => (
                            <tr key={row.index}><td style={{ padding: '0.9rem 1rem', borderBottom: '1px solid rgba(129, 160, 207, 0.12)' }}>{row.index}</td><td style={{ padding: '0.9rem 1rem', borderBottom: '1px solid rgba(129, 160, 207, 0.12)' }}>{row.upserted}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
        </>
      )}
    </section>
  )
}
