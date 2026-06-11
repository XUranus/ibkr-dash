import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import * as echarts from 'echarts/core'
import { TreemapChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'
import type { EChartsType } from 'echarts/core'
import { fetchPositions, fetchPositionDetail } from '@/api/positions'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import PieDistributionCard, { type PieSegmentItem } from '@/components/PieDistributionCard'
import PositionTable from '@/components/PositionTable'
import type { PositionDetailResponse, PositionItem, PositionListResponse, PositionSummaryResponse } from '@/types/positions'
import { formatNumber } from '@/utils/format'

echarts.use([TreemapChart, CanvasRenderer, TooltipComponent])

function changeColor(pct: number | null | undefined): string {
  if (pct == null) return 'rgba(60,70,85,0.7)'
  const clamped = Math.max(-8, Math.min(8, pct)) // Clamp to [-8, 8] for color range
  const t = (clamped + 8) / 16 // 0 = deep red, 0.5 = neutral, 1 = deep green
  // Red → Dark neutral → Green
  const r = Math.round(180 - t * 120) // 180 → 60
  const g = Math.round(50 + t * 130)  // 50 → 180
  const b = Math.round(45 + t * 30)   // 45 → 75
  return `rgb(${r},${g},${b})`
}

export default function PositionsView() {
  const { t } = useTranslation()
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
  const chartRef = useRef<HTMLDivElement | null>(null)
  const chartInstance = useRef<EChartsType | null>(null)

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
      setErrorMessage(err instanceof Error ? err.message : t('positions.failedToLoadPositions'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadPositions() }, [])

  // Initialize ECharts treemap
  useEffect(() => {
    if (!chartRef.current || !response?.items?.length) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    }

    const items = response.items
    const data = items.map((p) => {
      const changePct = p.previous_day_change_percent ?? 0
      return {
        name: p.symbol ?? '--',
        value: p.position_value ?? 0,
        changePct,
        description: p.description ?? '',
        itemStyle: {
          borderColor: 'rgba(8,11,18,0.8)',
          borderWidth: 2,
          gapWidth: 2,
        },
      }
    })

    chartInstance.current.setOption({
      tooltip: {
        formatter: (params: { data: { name: string; value: number; changePct: number; description: string } }) => {
          const d = params.data
          const changeSign = d.changePct >= 0 ? '+' : ''
          const changeColor = d.changePct >= 0 ? '#3dd68c' : '#f25c5c'
          return [
            `<div style="font-family: 'JetBrains Mono', monospace; min-width: 200px;">`,
            `<div style="font-weight:700; font-size:14px; margin-bottom:2px;">${d.name}</div>`,
            `<div style="color:#8a8d9e; font-size:11px; margin-bottom:8px;">${d.description}</div>`,
            `<div style="display:flex; justify-content:space-between; font-size:13px;">`,
            `<span style="color:#8a8d9e">Market Value</span>`,
            `<span>$${d.value.toLocaleString()}</span>`,
            `</div>`,
            `<div style="display:flex; justify-content:space-between; font-size:13px; margin-top:2px;">`,
            `<span style="color:#8a8d9e">Daily Change</span>`,
            `<span style="color:${changeColor}">${changeSign}${d.changePct.toFixed(2)}%</span>`,
            `</div>`,
            `</div>`,
          ].join('')
        },
      },
      series: [{
        type: 'treemap',
        data,
        width: '100%',
        height: '100%',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          position: 'inside',
          align: 'center',
          verticalAlign: 'middle',
          formatter: (params: { data: { name: string; value: number; changePct: number } }) => {
            const d = params.data
            if (d.value < 100) return ''
            const changeStr = d.changePct >= 0 ? `+${d.changePct.toFixed(1)}%` : `${d.changePct.toFixed(1)}%`
            return `{name|${d.name}}\n{change|${changeStr}}`
          },
          rich: {
            name: {
              fontSize: 13,
              fontWeight: 700,
              fontFamily: 'JetBrains Mono, monospace',
              color: '#fff',
              lineHeight: 18,
              align: 'center',
            },
            change: {
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: 'rgba(255,255,255,0.85)',
              lineHeight: 16,
              align: 'center',
            },
          },
        },
        upperLabel: { show: false },
        itemStyle: {
          borderColor: 'rgba(8,11,18,0.8)',
          borderWidth: 2,
          gapWidth: 2,
        },
        levels: [{
          itemStyle: {
            borderColor: '#080b12',
            borderWidth: 3,
            gapWidth: 3,
          },
        }],
        visualMin: 100,
        visualMap: {
          show: false,
          type: 'continuous',
          dimension: 'changePct',
          min: -10,
          max: 10,
          inRange: {
            color: ['#c0392b', '#e74c3c', '#7f8c8d', '#27ae60', '#1a7a42'],
          },
        },
      }],
    })

    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [response])

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
      { label: t('positions.stocks'), value: buckets.get('Stocks')?.value ?? 0, color: '#56d5ff', note: t('positions.stockAdrHoldings'), members: buckets.get('Stocks')?.members },
      { label: t('positions.fixedIncome'), value: buckets.get('Fixed Income')?.value ?? 0, color: '#6ee7b7', note: t('positions.treasuryBondEtfs'), members: buckets.get('Fixed Income')?.members },
      { label: t('positions.cash'), value: buckets.get('Cash')?.value ?? 0, color: '#8b7cff', note: t('positions.accountCashBalance'), members: [t('positions.usdCash')] },
    ].filter((item) => item.value > 0)
  }, [response, overview, t])

  const industryPieItems = useMemo<PieSegmentItem[]>(() => {
    const palette = ['#56d5ff', '#6ee7b7', '#8b7cff', '#ffb454', '#ff7b98', '#7dd3fc', '#c084fc']
    const noteMap: Record<string, string> = {
      'Semiconductor': t('positions.chipsProcessors'),
      'Software/Platform': t('positions.platformSocialFintech'),
      'E-Commerce': t('positions.onlineRetailCloud'),
      'EV/Mobility': t('positions.electricVehicles'),
      'Other': t('positions.otherHoldings'),
    }
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
        note: noteMap[label] ?? label,
        members: [...new Set(data.members)],
      }))
  }, [response, t])

  const summary = response?.summary ?? null

  async function openPositionDetail(item: PositionItem) {
    const symbol = `${item.symbol ?? ''}`.trim()
    if (!symbol) return
    const key = `${item.asset_class ?? 'UNKNOWN'}:${symbol}`
    setActiveDetail({ key, symbol, description: item.description ?? t('positions.noName'), detail: null })
    setDetailLoading(true)
    setDetailError('')
    setDetailVisible(true)
    try {
      const detail = await fetchPositionDetail({ symbol, asset_class: item.asset_class })
      setActiveDetail((prev) => prev?.key === key ? { ...prev, detail } : prev)
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : t('positions.failedToLoadDetail'))
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <section className="page-section">
      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          {/* Portfolio Treemap */}
          {response?.items && response.items.length > 0 && (
            <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
              <div className="surface-panel__content">
                <p className="eyebrow">{t('positions.portfolioOverview')}</p>
                <div ref={chartRef} style={{ width: '100%', height: 400, borderRadius: 'var(--radius-md)', overflow: 'hidden' }} />
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, marginTop: 8, fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  <span style={{ color: '#b43232' }}>▼ Down</span>
                  <div style={{ width: 120, height: 8, borderRadius: 4, background: 'linear-gradient(90deg, #b43232, #3c6e3c)' }} />
                  <span style={{ color: '#3c6e3c' }}>Up ▲</span>
                </div>
              </div>
            </section>
          )}

          {/* Summary cards */}
          <section className="summary-layout summary-layout--triple">
            <section className="surface-panel">
              <div className="surface-panel__content">
                <h3 className="summary-title">{t('positions.positionConcentration')}</h3>
                {!summary || summary.top_positions.length === 0 ? (
                  <div className="empty-state" style={{ minHeight: 'auto', padding: '2rem 1rem' }}>{t('positions.noConcentrationData')}</div>
                ) : (
                  <div className="summary-list">
                    {summary.top_positions.map((item) => (
                      <div key={`${item.asset_class}-${item.symbol}`} className="summary-list__row">
                        <div className="summary-list__meta">
                          <strong>{item.symbol ?? '--'}</strong>
                          <p>{item.description ?? t('positions.noName')}</p>
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

            <PieDistributionCard title={t('positions.assetClasses')} subtitle={t('positions.assetClassesDesc')} items={assetPieItems} />
            <PieDistributionCard title={t('positions.industryDistribution')} subtitle={t('positions.industryDistributionDesc')} items={industryPieItems} />
          </section>

          {/* Position table */}
          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">{t('positions.positionDetails')}</h2>
                  <p className="panel-subtitle">{t('positions.positionDetailsDesc')}</p>
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
              <h3 style={{ margin: 0 }}>{activeDetail?.symbol ? `${activeDetail.symbol} Detail` : t('positions.positionDetail')}</h3>
              <button className="btn btn--ghost" onClick={() => setDetailVisible(false)}>{t('positions.close')}</button>
            </div>
            {detailLoading ? <LoadingBlock /> : detailError ? <ErrorBlock message={detailError} /> : (
              <div style={{ color: 'var(--color-text-secondary)', minHeight: 200 }}>
                {activeDetail?.detail ? (
                  <div>
                    <p><strong>{activeDetail.detail.symbol}</strong> - {activeDetail.detail.description}</p>
                    <p>{t('positions.dailyBarsAndTradeMarkers', { bars: activeDetail.detail.bars.length, trades: activeDetail.detail.trades.length })}</p>
                    <p style={{ fontSize: '0.85rem', marginTop: 8 }}>{t('positions.chartPlaceholder')}</p>
                  </div>
                ) : (
                  <div className="empty-state">{t('positions.noDetailAvailable')}</div>
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </section>
  )
}
