import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { triggerImport, triggerAiReport, fetchImportHistory } from '@/api/adminScheduler'
import AdminTabs from '@/components/AdminTabs'
import type { ImportHistoryItem, TriggerAiReportResponse, TriggerImportResponse } from '@/types/adminScheduler'

export default function AdminSchedulerView() {
  const { t } = useTranslation()
  const [importRunning, setImportRunning] = useState(false)
  const [importResult, setImportResult] = useState<TriggerImportResponse | null>(null)
  const [aiRunning, setAiRunning] = useState(false)
  const [aiResult, setAiResult] = useState<TriggerAiReportResponse | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [importHistory, setImportHistory] = useState<ImportHistoryItem[]>([])
  const [loading, setLoading] = useState(true)

  const loadImportHistory = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchImportHistory(100)
      setImportHistory(data.items)
    } catch {
      // silently ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadImportHistory() }, [loadImportHistory])

  async function handleTriggerImport() {
    setImportRunning(true)
    setImportResult(null)
    try {
      const result = await triggerImport()
      setImportResult(result)
      await loadImportHistory()
    } catch (err) {
      setImportResult({ success: false, files: {}, errors: [err instanceof Error ? err.message : t('common.error')], started_at: '', duration_ms: 0 })
    } finally {
      setImportRunning(false)
    }
  }

  async function handleTriggerAiReport() {
    setAiRunning(true)
    setAiResult(null)
    setAiError(null)
    try {
      const result = await triggerAiReport()
      setAiResult(result)
    } catch (err) {
      setAiError(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setAiRunning(false)
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
  }

  function formatRecords(records: Record<string, number> | null): string {
    if (!records) return '-'
    return Object.entries(records)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')
  }

  function formatDuration(ms: number | null): string {
    if (!ms || ms <= 0) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('admin.title')}</p>
              <h2 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-text-bright)' }}>{t('adminScheduler.title')}</h2>
              <p className="panel-subtitle">{t('adminScheduler.subtitle')}</p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {/* Trigger section */}
      <section className="surface-panel">
        <div className="surface-panel__content" style={{ padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <button
              className="btn btn--sm btn--accent"
              onClick={handleTriggerImport}
              disabled={importRunning}
            >
              {importRunning ? t('adminScheduler.triggering') : t('adminScheduler.triggerImport')}
            </button>
            {importResult && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                color: importResult.success ? 'var(--color-positive)' : 'var(--color-negative)',
              }}>
                {importResult.success
                  ? `${t('adminScheduler.triggerSuccess')} (${Object.keys(importResult.files).length} files, ${formatDuration(importResult.duration_ms)})`
                  : `${t('adminScheduler.triggerFailed')}: ${importResult.errors.join('; ')}`}
              </span>
            )}
            <button
              className="btn btn--sm btn--ghost"
              onClick={handleTriggerAiReport}
              disabled={aiRunning}
            >
              {aiRunning ? t('adminScheduler.aiGenerating') : t('adminScheduler.triggerAiReport')}
            </button>
            {aiResult && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-positive)',
              }}>
                {t('adminScheduler.aiSuccess')} ({formatDuration(aiResult.duration_ms)})
              </span>
            )}
            {aiError && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-negative)',
              }}>
                {t('adminScheduler.aiFailed')}: {aiError}
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Import history table */}
      <section className="surface-panel">
        <div className="surface-panel__content" style={{ padding: '12px 14px' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text-bright)', marginBottom: 10, fontFamily: 'var(--font-mono)' }}>
            {t('adminScheduler.historyTitle')}
          </div>
          {loading ? (
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>{t('common.loading')}</div>
          ) : importHistory.length === 0 ? (
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', padding: '8px 0' }}>
              {t('adminScheduler.noHistory')}
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.triggerTime')}</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.filePath')}</th>
                    <th style={{ textAlign: 'right', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.fileSize')}</th>
                    <th style={{ textAlign: 'center', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.status')}</th>
                    <th style={{ textAlign: 'right', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.duration')}</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--color-text-muted)' }}>{t('adminScheduler.table.records')}</th>
                  </tr>
                </thead>
                <tbody>
                  {importHistory.map((item) => (
                    <tr key={item.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <td style={{ padding: '6px 8px', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{item.started_at || item.run_at}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--color-text-bright)', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.file_path}>
                        {item.file_path.split('/').pop() || item.file_path}
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--color-text-secondary)' }}>{formatBytes(item.file_size)}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                        <span className={`tag ${item.status === 'success' ? 'tag--positive' : 'tag--negative'}`}>
                          {t(`adminScheduler.status.${item.status}`, { defaultValue: item.status })}
                        </span>
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{formatDuration(item.duration_ms)}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--color-text-secondary)', fontSize: '0.7rem' }}>{formatRecords(item.records_imported)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </section>
  )
}
