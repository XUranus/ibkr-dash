import { useState, useEffect, useMemo, useCallback } from 'react'
import { fetchPositions, fetchPositionDetail } from '@/api/positions'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import PieDistributionCard, { type PieSegmentItem } from '@/components/PieDistributionCard'
import PositionTable from '@/components/PositionTable'
import type { PositionDetailResponse, PositionItem, PositionListResponse, PositionSummaryResponse } from '@/types/positions'
import { formatNumber } from '@/utils/format'

export default function PositionsView() {
  const { overview, ensureLoaded } = useAccountOverview()
  const [response, setResponse] = useState<PositionListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [activeDetail, setActiveDetail] = useState<{
    key: string; symbol: string; description: string; detail: PositionDetailResponse | null
  } | null>(null)

  async function loadPositions() {
    setLoading(true)
    setErrorMessage('')
    try {
      const [listResponse] = await Promise.all([
        fetchPositions({ include_summary: true, sort_by: 'position_value', sort_order: 'desc', page: 1, page_size: 200 }),
        ensureLoaded(),
      ])
      setResponse(listResponse)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load positions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadPositions() }, [])

  function classifyAssetBucket(item: PositionItem): string {
    const desc = `${item.description ?? ''}`.toUpperCase()
    const sym = `${item.symbol ?? ''}`.toUpperCase()
    if (desc.includes('TREASURY') || desc.includes('BOND') || desc.includes('0-3 MONTH') || sym === 'SGOV') return 'Fixed Income'
    if (item.asset_class === 'STK') return 'Stocks'
    return 'Other'
  }

  function classifyIndustry(item: PositionItem): string {
    const text = `${item.symbol ?? ''} ${item.description ?? ''}`.toUpperCase()
    if (text.includes('AMD') || text.includes('ARM') || text.includes('INTEL') || text.includes('QUALCOMM')) return 'Semiconductor'
    if (text.includes('MICROSOFT') || text.includes('META') || text.includes('STRATEGY')) return 'Software/Platform'
    if (text.includes('AMAZON')) return 'E-Commerce'
    if (text.includes('TESLA')) return 'EV/Mobility'
    return 'Other'
  }

  const assetPieItems = useMemo<PieSegmentItem[]>(() => {
    const buckets = new Map<string, { value: number; members: string[] }>([
      ['Stocks', { value: 0, members: [] }],
      ['Fixed Income', { value: 0, members: [] }],
      ['Cash', { value: Math.max(overview?.cash ?? 0, 0), members: ['Account Cash'] }],
    ])
    response?.items.forEach((item) => {
      const bucket = classifyAssetBucket(item)
      const cur = buckets.get(bucket) ?? { value: 0, members: [] }
      cur.value += item.position_value ?? 0
      cur.members.push(item.symbol ?? item.description ?? '--')
      buckets.set(bucket, cur)
    })
    return [
      { label: 'Stocks', value: buckets.get('Stocks')?.value ?? 0, color: '#56d5ff', note: 'Stock & ADR holdings', members: buckets.get('Stocks')?.members },
      { label: 'Fixed Income', value: buckets.get('Fixed Income')?.value ?? 0, color: '#6ee7b7', note: 'Treasury / Bond ETFs', members: buckets.get('Fixed Income')?.members },
      { label: 'Cash', value: buckets.get('Cash')?.value ?? 0, color: '#8b7cff', note: 'Account cash balance', members: ['USD Cash'] },
    ].filter((item) => item.value > 0)
  }, [response, overview])

  const industryPieItems = useMemo<PieSegmentItem[]>(() => {
    const palette = ['#56d5ff', '#6ee7b7', '#8b7cff', '#ffb454', '#ff7b98', '#7dd3fc', '#c084fc']
    const buckets = new Map<string, { value: number; members: string[] }>()
    response?.items.forEach((item) => {
      const industry = classifyIndustry(item)
      const cur = buckets.get(industry) ?? { value: 0, members: [] }
      cur.value += item.position_value ?? 0
      cur.members.push(item.symbol ?? item.description ?? '--')
      buckets.set(industry, cur)
    })
    return Array.from(buckets.entries())
      .sort((a, b) => b[1].value - a[1].value)
      .map(([label, data], i) => ({
        label, value: data.value, color: palette[i % palette.length],
        note: label === 'Semiconductor' ? 'Chips / Processors' : label === 'Software/Platform' ? 'Platform / Social / Fintech' : label === 'E-Commerce' ? 'Online Retail / Cloud' : label === 'EV/Mobility' ? 'Electric Vehicles' : 'Other holdings',
        members: [...new Set(data.members)],
      }))
  }, [response])

  const summary = response?.summary ?? null

  async function openPositionDetail(item: PositionItem) {
    const symbol = `${item.symbol ?? ''}`.trim()
    if (!symbol) return
    const key = `${item.asset_class ?? 'UNKNOWN'}:${symbol}`
    setActiveDetail({ key, symbol, description: item.description ?? 'No name', detail: null })
    setDetailLoading(true)
    setDetailError('')
    setDetailVisible(true)
    try {
      const detail = await fetchPositionDetail({ symbol, asset_class: item.asset_class })
      setActiveDetail((prev) => prev?.key === key ? { ...prev, detail } : prev)
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load detail')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <section className="page-section">
      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          <section className="summary-layout summary-layout--triple">
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="summary-title">Position Concentration</h3>
                {!summary || summary.top_positions.length === 0 ? (
                  <div className="empty-state" style={{ minHeight: 'auto', padding: '2rem 1rem' }}>No concentration data</div>
                ) : (
                  <div className="summary-list">
                    {summary.top_positions.map((item) => (
                      <div key={`${item.asset_class}-${item.symbol}`} className="summary-list__row">
                        <div className="summary-list__meta">
                          <strong>{item.symbol ?? '--'}</strong>
                          <p>{item.description ?? 'No name'}</p>
                        </div>
                        <div className="summary-list__value">
                          <strong>{formatNumber(item.position_value, 2)}</strong>
                          <span>{item.percent_of_nav === null ? '--' : `${formatNumber(item.percent_of_nav, 2)}%`}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <PieDistributionCard title="Asset Classes" subtitle="Stocks, fixed income, and cash allocation" items={assetPieItems} />
            <PieDistributionCard title="Industry Distribution" subtitle="Lightweight industry classification by symbol and description" items={industryPieItems} />
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">Position Details</h2>
                  <p className="panel-subtitle">Click column headers to sort. Click any row to view stock detail chart.</p>
                </div>
              </div>
              {response && <PositionTable items={response.items} onSelect={openPositionDetail} />}
            </div>
          </section>
        </>
      )}

      {detailVisible && (
        <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setDetailVisible(false) }}>
          <section className="modal-dialog" style={{ width: 'min(1400px, 94vw)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>{activeDetail?.symbol ? `${activeDetail.symbol} Detail` : 'Position Detail'}</h3>
              <button className="btn btn--ghost" onClick={() => setDetailVisible(false)}>Close</button>
            </div>
            {detailLoading ? <LoadingBlock /> : detailError ? <ErrorBlock message={detailError} /> : (
              <div style={{ color: 'var(--color-text-secondary)', minHeight: 200 }}>
                {activeDetail?.detail ? (
                  <div>
                    <p><strong>{activeDetail.detail.symbol}</strong> - {activeDetail.detail.description}</p>
                    <p>{activeDetail.detail.bars.length} daily bars, {activeDetail.detail.trades.length} trade markers</p>
                    <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Position detail chart with candlestick and trade markers will render here.</p>
                  </div>
                ) : (
                  <div className="empty-state">No detail available</div>
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </section>
  )
}
