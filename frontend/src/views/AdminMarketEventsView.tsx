/** Admin market events page -- manage and sync market events. */

import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'
import type { MarketEvent } from '@/types/marketEvent'

export default function AdminMarketEventsView() {
  const [events, setEvents] = useState<MarketEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const loadEvents = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: MarketEvent[] }>('/api/admin/market-events?limit=100')
      setEvents(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadEvents() }, [loadEvents])

  async function handleSeed() {
    setSeeding(true)
    try {
      await request('/api/admin/market-events/seed', { method: 'POST' })
      await loadEvents()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to seed events')
    } finally {
      setSeeding(false)
    }
  }

  async function handleSync() {
    setSyncing(true)
    try {
      await request('/api/admin/market-events/sync', { method: 'POST' })
      await loadEvents()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sync events')
    } finally {
      setSyncing(false)
    }
  }

  async function handleDelete(eventId: string) {
    if (!confirm('Delete this event?')) return
    try {
      await request(`/api/admin/market-events/${eventId}`, { method: 'DELETE' })
      setEvents((prev) => prev.filter((e) => e.id !== eventId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete event')
    }
  }

  function formatDate(iso: string): string {
    if (!iso) return '--'
    try {
      return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    } catch {
      return iso.slice(0, 10)
    }
  }

  function importanceTagClass(importance: string): string {
    if (importance === 'CRITICAL') return 'tag--negative'
    if (importance === 'HIGH') return 'tag--warning'
    if (importance === 'MEDIUM') return 'tag--accent'
    return 'tag--neutral'
  }

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">Admin</p>
        <h1 className="page-title">Market Events Management</h1>
        <p className="page-subtitle">Seed and sync market events from external sources</p>
      </header>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)' }}>
        <button className="btn btn--accent btn--sm" onClick={handleSeed} disabled={seeding}>
          {seeding ? 'Seeding...' : 'Seed Events'}
        </button>
        <button className="btn btn--ghost btn--sm" onClick={handleSync} disabled={syncing}>
          {syncing ? 'Syncing...' : 'Sync from Sources'}
        </button>
        <button className="btn btn--ghost btn--sm" onClick={loadEvents} disabled={loading}>
          Refresh
        </button>
      </div>

      <div className="surface-panel">
        <div className="surface-panel__content" style={{ padding: 0 }}>
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : events.length === 0 ? (
            <div className="empty-state">No events found. Click "Seed Events" to populate.</div>
          ) : (
            <div className="table-shell">
              <table className="data-table" style={{ minWidth: 900 }}>
                <thead>
                  <tr>
                    <th style={{ width: '12%' }}>Date</th>
                    <th style={{ width: '25%' }}>Title</th>
                    <th style={{ width: '12%' }}>Type</th>
                    <th style={{ width: '12%' }}>Category</th>
                    <th style={{ width: '12%' }}>Importance</th>
                    <th style={{ width: '15%' }}>Source</th>
                    <th style={{ width: '12%', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id}>
                      <td><span className="terminal-muted">{formatDate(e.scheduled_at)}</span></td>
                      <td>
                        <div className="table-symbol">
                          <span className="table-symbol__code">{e.title}</span>
                        </div>
                      </td>
                      <td><span className="terminal-muted">{e.event_type}</span></td>
                      <td><span className="tag tag--accent">{e.category}</span></td>
                      <td><span className={`tag ${importanceTagClass(e.importance)}`}>{e.importance}</span></td>
                      <td><span className="terminal-muted">{e.source}</span></td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          className="btn btn--ghost btn--sm"
                          onClick={() => handleDelete(e.id)}
                          style={{ color: 'var(--color-negative)', fontSize: '0.78rem' }}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
