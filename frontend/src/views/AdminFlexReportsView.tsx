/** Admin Flex Reports page -- manage downloaded IBKR Flex XML reports. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import AdminTabs from '@/components/AdminTabs'

interface FlexReport {
  name: string
  size: number
  modified_at: string
  query_id: string
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  if (!iso) return '--'
  try {
    const d = new Date(iso)
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso.slice(0, 16)
  }
}

export default function AdminFlexReportsView() {
  const { t } = useTranslation()
  const [files, setFiles] = useState<FlexReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<string | null>(null)
  const [downloadingAll, setDownloadingAll] = useState(false)

  const loadFiles = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<FlexReport[]>('/api/admin/flex-reports')
      setFiles(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('flexReports.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadFiles() }, [loadFiles])

  async function handleDelete(name: string) {
    if (!confirm(t('flexReports.confirmDelete', { name }))) return
    setDeleting(name)
    try {
      await request(`/api/admin/flex-reports/${encodeURIComponent(name)}`, { method: 'DELETE' })
      setFiles((prev) => prev.filter((f) => f.name !== name))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('flexReports.failedToDelete'))
    } finally {
      setDeleting(null)
    }
  }

  function handleDownload(name: string) {
    const url = `/api/admin/flex-reports/download/${encodeURIComponent(name)}`
    window.open(url, '_blank')
  }

  async function handleDownloadAll() {
    setDownloadingAll(true)
    try {
      window.open('/api/admin/flex-reports/download-all', '_blank')
    } finally {
      setDownloadingAll(false)
    }
  }

  const totalSize = files.reduce((sum, f) => sum + f.size, 0)

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <AdminTabs />
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">Admin</p>
        <h1 className="page-title">{t('flexReports.title')}</h1>
        <p className="page-subtitle">{t('flexReports.subtitle')}</p>
      </header>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)', alignItems: 'center' }}>
        <button className="btn btn--accent btn--sm" onClick={handleDownloadAll} disabled={downloadingAll || files.length === 0}>
          {downloadingAll ? '...' : `${t('flexReports.downloadAll')} (${files.length}, ${formatBytes(totalSize)})`}
        </button>
        <button className="btn btn--ghost btn--sm" onClick={loadFiles} disabled={loading}>
          {loading ? t('flexReports.loading') : t('flexReports.refresh')}
        </button>
      </div>

      {loading && files.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{t('flexReports.loading')}</p>
      ) : files.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{t('flexReports.noReports')}</p>
      ) : (
        <div className="table-shell">
          <table className="data-table" style={{ minWidth: 800 }}>
            <thead>
              <tr>
                <th style={{ width: '30%', textAlign: 'left' }}>{t('flexReports.fileName')}</th>
                <th style={{ width: '12%', textAlign: 'center' }}>{t('flexReports.queryId')}</th>
                <th style={{ width: '12%', textAlign: 'right' }}>{t('flexReports.size')}</th>
                <th style={{ width: '24%', textAlign: 'left' }}>{t('flexReports.downloadedAt')}</th>
                <th style={{ width: '22%', textAlign: 'center' }}>{t('flexReports.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.name}>
                  <td>
                    <span className="table-symbol__code">{f.name}</span>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className="tag tag--accent">{f.query_id}</span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontVariantNumeric: 'tabular-nums' }}>
                    {formatBytes(f.size)}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                    {formatTime(f.modified_at)}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => handleDownload(f.name)}
                      >
                        {t('flexReports.download')}
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => handleDelete(f.name)}
                        disabled={deleting === f.name}
                        style={{ color: 'var(--color-negative)' }}
                      >
                        {deleting === f.name ? '...' : t('flexReports.delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
