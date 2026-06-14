import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import * as echarts from 'echarts/core'
import { TreemapChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'
import type { EChartsType } from 'echarts/core'
import { fetchPositions, fetchPositionDetail, fetchRealtimePositions, type RealtimePosition } from '@/api/positions'
import { useAccountOverview } from '@/hooks/useAccountOverview'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import Modal from '@/components/Modal'
import PieDistributionCard, { type PieSegmentItem } from '@/components/PieDistributionCard'
import PositionAnalysisCard from '@/components/PositionAnalysisCard'
import PositionTable from '@/components/PositionTable'
import type { PositionDetailResponse, PositionItem, PositionListResponse, PositionSummaryResponse } from '@/types/positions'
import { formatNumber } from '@/utils/format'

echarts.use([TreemapChart, CanvasRenderer, TooltipComponent])

function changeColor(pct: number | null | undefined): string {
  if (pct == null) return '#3a4555'
  if (pct >= 0) {
    // Green: intensity scales with magnitude
    const intensity = Math.min(pct / 5, 1)
    const g = Math.round(130 + intensity * 70)
    return `rgb(30,${g},60)`
  } else {
    // Red: intensity scales with magnitude
    const intensity = Math.min(Math.abs(pct) / 5, 1)
    const r = Math.round(150 + intensity * 70)
    return `rgb(${r},35,40)`
  }
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
  const [realtimePositions, setRealtimePositions] = useState<RealtimePosition[]>([])
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  async function loadPositions() {
    setLoading(true)
    setErrorMessage('')
    try {
      const [listResponse, , realtimeResult] = await Promise.all([
        fetchPositions({ include_summary: true, sort_by: 'position_value', sort_order: 'desc', page: 1, page_size: 200 }),
        ensureLoaded(),
        fetchRealtimePositions().catch(() => ({ items: [] as RealtimePosition[], count: 0 })),
      ])
      setResponse(listResponse)
      if (realtimeResult.items?.length) {
        setRealtimePositions(realtimeResult.items)
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('positions.failedToLoadPositions'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPositions()
    // Auto-refresh realtime data every 60 seconds
    refreshTimer.current = setInterval(async () => {
      try {
        const rt = await fetchRealtimePositions()
        if (rt.items?.length) setRealtimePositions(rt.items)
      } catch {
        // Silent fail for background refresh
      }
    }, 60000)
    return () => { if (refreshTimer.current) clearInterval(refreshTimer.current) }
  }, [])

  // Initialize ECharts treemap
  useEffect(() => {
    if (!chartRef.current || !response?.items?.length) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    }

    const items = response.items
    // Build a lookup of realtime change data
    const rtMap = new Map<string, number>()
    for (const rt of realtimePositions) {
      rtMap.set(rt.symbol, rt.change_pct ?? 0)
    }
    const data = items.map((p) => {
      const changePct = rtMap.get(p.symbol ?? '') ?? p.previous_day_change_percent ?? 0
      return {
        name: p.symbol ?? '--',
        value: p.position_value ?? 0,
        changePct,
        description: p.description ?? '',
        itemStyle: {
          color: changeColor(changePct),
          borderColor: 'rgba(8,11,18,0.9)',
          borderWidth: 2,
          gapWidth: 2,
        },
      }
    })

    chartInstance.current.setOption({
      tooltip: {
        formatter: (params: { data: { name: string; value: number; changePct: number; description: string } }) => {
          const d = params.data
          const pct = d.changePct ?? 0
          const changeSign = pct >= 0 ? '+' : ''
          const changeColorHex = pct >= 0 ? '#3dd68c' : '#f25c5c'
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
            `<span style="color:${changeColorHex}">${changeSign}${pct.toFixed(2)}%</span>`,
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
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 700,
          color: '#fff',
          fontSize: 16,
          formatter: (params: { data: { name: string; value: number; changePct: number } }) => {
            const d = params.data
            if (!d || d.value < 100) return ''
            const changeStr = d.changePct >= 0 ? `+${d.changePct.toFixed(1)}%` : `${d.changePct.toFixed(1)}%`
            return `${d.name}\n${changeStr}`
          },
        },
        upperLabel: { show: false },
        itemStyle: {
          borderColor: 'rgba(8,11,18,0.9)',
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
      }],
    })

    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [response, realtimePositions])

  function classifyAssetBucket(item: PositionItem): string {
    const desc = `${item.description ?? ''}`.toUpperCase()
    const sym = `${item.symbol ?? ''}`.toUpperCase()
    if (item.asset_class === 'OPT') return 'Options'
    if (desc.includes('TREASURY') || desc.includes('BOND') || desc.includes('0-3 MONTH') || sym === 'SGOV') return 'Fixed Income'
    if (item.asset_class === 'STK') return 'Stocks'
    return 'Other'
  }

  function classifyIndustry(item: PositionItem): string {
    const text = `${item.symbol ?? ''} ${item.description ?? ''}`.toUpperCase()
    const assetClass = item.asset_class ?? ''

    // Options — group by underlying
    if (assetClass === 'OPT') return 'Options'

    // Semiconductor
    if (text.includes('AVGO') || text.includes('BROADCOM') ||
        text.includes('MRVL') || text.includes('MARVELL') ||
        text.includes('TXN') || text.includes('TEXAS INSTRUMENT') ||
        text.includes('SITIME') || text.includes('SITM') ||
        text.includes('AAOI') || text.includes('APPLIED OPTO') ||
        text.includes('SK HYNIX') || text.includes('000660') ||
        text.includes('BESI') || text.includes('BE SEMICONDUCTOR') ||
        text.includes('NVDA') || text.includes('NVIDIA')) return 'Semiconductor'

    // Internet / Cloud / Fintech
    if (text.includes('GOOG') || text.includes('ALPHABET') ||
        text.includes('NET') || text.includes('CLOUDFLARE') ||
        text.includes('CRCL') || text.includes('CIRCLE') ||
        text.includes('HOOD') || text.includes('ROBINHOOD')) return 'Internet/Cloud'

    // E-Commerce / Consumer Tech
    if (text.includes('PDD') || text.includes('BABA') || text.includes('ALIBABA') ||
        text.includes('CPNG') || text.includes('COUPANG') ||
        text.includes('YUMC') || text.includes('YUM CHINA')) return 'E-Commerce/Consumer'

    // Software / Enterprise
    if (text.includes('MSTR') || text.includes('STRATEGY') ||
        text.includes('ROP') || text.includes('ROPER') ||
        text.includes('SMCI') || text.includes('SUPER MICRO')) return 'Software/Enterprise'

    // Energy / Nuclear
    if (text.includes('SMR') || text.includes('NUSCALE') ||
        text.includes('LEU') || text.includes('CENTRUS') ||
        text.includes('OKLO')) return 'Energy/Nuclear'

    // Materials / Mining
    if (text.includes('MP') || text.includes('MP MATERIAL') ||
        text.includes('COPX') || text.includes('COPPER') ||
        text.includes('TMC') || text.includes('METALS CO') ||
        text.includes('USAR') || text.includes('RARE EARTH')) return 'Materials/Mining'

    // Precious Metals
    if (text.includes('IAU') || text.includes('GOLD') ||
        text.includes('IAUI')) return 'Precious Metals'

    // Treasuries / Fixed Income
    if (text.includes('SHV') || text.includes('SGOV') ||
        text.includes('TREASURY') || text.includes('BOND')) return 'Treasuries'

    // Consumer / Staples
    if (text.includes('PG') || text.includes('PROCTER')) return 'Consumer/Staples'

    // Telecom
    if (text.includes('NOK') || text.includes('NOKIA')) return 'Telecom'

    return 'Other'
  }

  const assetPieItems = useMemo<PieSegmentItem[]>(() => {
    const buckets = new Map<string, { value: number; members: string[] }>([
      ['Stocks', { value: 0, members: [] }],
      ['Options', { value: 0, members: [] }],
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
      { label: 'Stocks', value: buckets.get('Stocks')?.value ?? 0, color: '#56d5ff', note: 'Stocks, ADRs, ETFs', members: buckets.get('Stocks')?.members },
      { label: 'Options', value: buckets.get('Options')?.value ?? 0, color: '#ffb454', note: 'Options contracts', members: buckets.get('Options')?.members },
      { label: 'Fixed Income', value: buckets.get('Fixed Income')?.value ?? 0, color: '#6ee7b7', note: 'Treasury & bond ETFs', members: buckets.get('Fixed Income')?.members },
      { label: 'Cash', value: buckets.get('Cash')?.value ?? 0, color: '#8b7cff', note: 'Account cash balance', members: ['USD Cash'] },
    ].filter((item) => item.value > 0)
  }, [response, overview, t])

  const industryPieItems = useMemo<PieSegmentItem[]>(() => {
    const palette = ['#56d5ff', '#6ee7b7', '#8b7cff', '#ffb454', '#ff7b98', '#7dd3fc', '#c084fc', '#f59e0b', '#10b981', '#6366f1', '#ec4899']
    const noteMap: Record<string, string> = {
      'Semiconductor': 'Chips, processors, equipment',
      'Internet/Cloud': 'Search, cloud, fintech',
      'E-Commerce/Consumer': 'Online retail, food delivery',
      'Software/Enterprise': 'Enterprise software, servers',
      'Energy/Nuclear': 'Nuclear, uranium, clean energy',
      'Materials/Mining': 'Rare earth, copper, metals',
      'Precious Metals': 'Gold ETFs',
      'Treasuries': 'Short-term government bonds',
      'Consumer/Staples': 'Consumer goods',
      'Telecom': 'Telecom equipment',
      'Options': 'Options contracts',
      'Other': 'Other holdings',
    }
    const buckets = new Map<string, { value: number; members: string[] }>()
    response?.items.forEach((item) => {
      const industry = classifyIndustry(item)
      const cur = buckets.get(industry) ?? { value: 0, members: [] }
      cur.value += item.position_value ?? 0
      cur.members.push(item.symbol ?? item.description ?? '--')
      buckets.set(industry, cur)
    })
    // Top 5 industries + aggregate the rest into "Other"
    const sorted = Array.from(buckets.entries()).sort((a, b) => b[1].value - a[1].value)
    const top5 = sorted.slice(0, 5)
    const rest = sorted.slice(5)
    if (rest.length > 0) {
      const otherValue = rest.reduce((sum, [, d]) => sum + d.value, 0)
      const otherMembers = rest.flatMap(([, d]) => d.members)
      top5.push(['Other', { value: otherValue, members: otherMembers }])
    }
    return top5
      .filter(([, data]) => data.value > 0)
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
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 8, fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  <span style={{ color: '#c83232' }}>▼ Red = Down</span>
                  <span style={{ color: 'var(--color-text-muted)', opacity: 0.3 }}>|</span>
                  <span style={{ color: '#2ca850' }}>Green = Up ▲</span>
                </div>
              </div>
            </section>
          )}

          {/* Distribution charts + AI Analysis */}
          <section className="grid-3col">
            <PieDistributionCard title={t('positions.assetClasses')} subtitle={t('positions.assetClassesDesc')} items={assetPieItems} />
            <PieDistributionCard title={t('positions.industryDistribution')} subtitle={t('positions.industryDistributionDesc')} items={industryPieItems} />
            <PositionAnalysisCard />
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

      <Modal
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        title={activeDetail?.symbol ? `${activeDetail.symbol} Detail` : t('positions.positionDetail')}
        width="min(1400px, 94vw)"
      >
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
      </Modal>
    </section>
  )
}
