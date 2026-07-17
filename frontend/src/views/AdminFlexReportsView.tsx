/** Admin Flex Reports page -- manage downloaded IBKR Flex XML reports. */

import { useState, useEffect, useCallback } from 'react'
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
      setError(err instanceof Error ? err.message : 'Failed to load reports')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadFiles() }, [loadFiles])

  async function handleDelete(name: string) {
    if (!confirm(`Delete ${name}?`)) return
    setDeleting(name)
    try {
      await request(`/api/admin/flex-reports/${encodeURIComponent(name)}`, { method: 'DELETE' })
      setFiles((prev) => prev.filter((f) => f.name !== name))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete')
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
      const url = '/api/admin/flex-reports/download-all'
      window.open(url, '_blank')
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
        <h1 className="page-title">Flex Reports</h1>
        <p className="page-subtitle">Manage downloaded IBKR Flex Web Service XML reports</p>
      </header>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)', alignItems: 'center' }}>
        <button className="btn btn--accent btn--sm" onClick={handleDownloadAll} disabled={downloadingAll || files.length === 0}>
          {downloadingAll ? 'Packing...' : `Download All (${files.length} files, ${formatBytes(totalSize)})`}
        </button>
        <button className="btn btn--ghost btn--sm" onClick={loadFiles} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {loading && files.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>Loading...</p>
      ) : files.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>No flex reports found.</p>
      ) : (
        <div className="surface-panel" style={{ overflow: 'auto' }}>
          <table className="table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>File Name</th>
                <th style={{ textAlign: 'left' }}>Query ID</th>
                <th style={{ textAlign: 'right' }}>Size</th>
                <th style={{ textAlign: 'left' }}>Downloaded At</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.name}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{f.name}</td>
                  <td>
                    <span className="tag tag--accent">{f.query_id}</span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
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
                        title="Download"
                      >
                        Download
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => handleDelete(f.name)}
                        disabled={deleting === f.name}
                        style={{ color: 'var(--color-negative)' }}
                        title="Delete"
                      >
                        {deleting === f.name ? 'Deleting...' : 'Delete'}
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
