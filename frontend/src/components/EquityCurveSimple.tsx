import { useState, useRef, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EquityCurvePoint } from '@/types/charts'
import type { EquityCurveRangeKey, EquityCurveRangeOption } from '@/utils/equityCurveRange'
import { formatNumber } from '@/utils/format'

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, CanvasRenderer])

type ChartMode = 'pnl' | 'equity'

interface Props {
  items: EquityCurvePoint[]
  loading: boolean
  errorMessage: string
  rangeOptions: EquityCurveRangeOption[]
  selectedRange: EquityCurveRangeKey
  onSelectRange: (range: EquityCurveRangeKey) => void
}

export default function EquityCurveSimple({ items, loading, errorMessage, rangeOptions, selectedRange, onSelectRange }: Props) {
  const { t } = useTranslation()
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)
  const [mode, setMode] = useState<ChartMode>('pnl')

  const renderChart = useCallback(() => {
    if (!chartInstance.current || items.length === 0) return

    const equityData: [string, number][] = []
    const pnlData: [string, number][] = []
    const costData: [string, number][] = []
    const realizedData: [string, number][] = []

    items.forEach((item) => {
      if (item.total_equity !== null) equityData.push([item.report_date, item.total_equity])
      if (item.total_pnl !== null) pnlData.push([item.report_date, item.total_pnl])
      if (item.net_cost !== null) costData.push([item.report_date, item.net_cost])
      if (item.realized_pnl !== null) realizedData.push([item.report_date, item.realized_pnl])
    })

    const pnlSeries = [
      {
        name: t('dashboard.netPnl'), type: 'line', smooth: 0.18, sampling: 'lttb',
        data: pnlData, lineStyle: { width: 2, color: '#3FB950' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(63, 185, 80, 0.12)' },
          { offset: 1, color: 'rgba(63, 185, 80, 0.01)' },
        ]) },
        showSymbol: false,
      },
      {
        name: t('dashboard.realizedPnl'), type: 'line', smooth: 0.12, sampling: 'lttb',
        data: realizedData, lineStyle: { width: 1.5, color: '#D29922' },
        showSymbol: false,
      },
    ]

    const equitySeries = [
      {
        name: t('dashboard.totalEquity'), type: 'line', smooth: 0.15, sampling: 'lttb',
        data: equityData, lineStyle: { width: 2, color: '#58A6FF' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(88, 166, 255, 0.12)' },
          { offset: 1, color: 'rgba(88, 166, 255, 0.01)' },
        ]) },
        showSymbol: false,
      },
      {
        name: t('dashboard.netCost'), type: 'line', step: 'end',
        data: costData, lineStyle: { width: 1.5, color: '#6E7681' },
        showSymbol: false,
      },
    ]

    chartInstance.current.setOption({
      animationDuration: 400,
      backgroundColor: 'transparent',
      grid: { top: 48, right: 60, bottom: 72, left: 20 },
      legend: { show: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#111820',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        textStyle: { color: '#C9D1D9', fontSize: 12 },
        padding: 10,
        valueFormatter: (val: number) => formatNumber(val),
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisTick: { show: false },
        axisLabel: { color: '#484F58', fontSize: 11, margin: 12 },
        splitLine: { show: false },
      },
      yAxis: [{
        type: 'value',
        position: 'right',
        axisLabel: { color: '#484F58', fontSize: 11 },
        splitNumber: 4,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
      }],
      dataZoom: [
        { type: 'inside', xAxisIndex: 0 },
        {
          type: 'slider', xAxisIndex: 0, height: 18, bottom: 16,
          borderColor: 'rgba(255,255,255,0.06)',
          backgroundColor: '#0A0E14',
          fillerColor: 'rgba(88, 166, 255, 0.1)',
          handleStyle: { color: '#151C28', borderColor: '#58A6FF' },
          textStyle: { color: '#484F58', fontSize: 10 },
        },
      ],
      series: mode === 'pnl' ? pnlSeries : equitySeries,
    }, true)
  }, [items, mode])

  useEffect(() => {
    if (!chartRef.current) return
    chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })

    const handleResize = () => chartInstance.current?.resize()
    const observer = new ResizeObserver(handleResize)
    observer.observe(chartRef.current)
    window.addEventListener('resize', handleResize)

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', handleResize)
      chartInstance.current?.dispose()
      chartInstance.current = null
    }
  }, [])

  useEffect(() => { renderChart() }, [renderChart])

  return (
    <div className="surface-panel" style={{ position: 'relative', overflow: 'hidden' }}>
      <div className="surface-panel__content">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <p className="eyebrow" style={{ margin: 0 }}>{t('dashboard.curves')}</p>
            <div style={{ display: 'flex', gap: 2 }}>
              <button
                type="button"
                className={`btn btn--sm ${mode === 'pnl' ? 'btn--accent' : ''}`}
                onClick={() => setMode('pnl')}
              >
                {t('dashboard.modePnl')}
              </button>
              <button
                type="button"
                className={`btn btn--sm ${mode === 'equity' ? 'btn--accent' : ''}`}
                onClick={() => setMode('equity')}
              >
                {t('dashboard.modeEquity')}
              </button>
            </div>
            <span className="tag">{items.length > 0 ? `${items[0].report_date} – ${items[items.length - 1].report_date}` : t('dashboard.noHistory')}</span>
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {rangeOptions.map((opt) => (
              <button
                key={opt.key}
                type="button"
                className={`btn btn--sm ${selectedRange === opt.key ? 'btn--accent' : ''}`}
                onClick={() => onSelectRange(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {items.length === 0 ? (
          <div className="empty-state">{errorMessage || t('dashboard.noCurveData')}</div>
        ) : (
          <>
            {loading && (
              <div style={{
                position: 'absolute', inset: 0, zIndex: 3,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(10, 14, 20, 0.5)',
                color: 'var(--color-text-secondary)', fontSize: '0.82rem',
              }}>
                {t('dashboard.updatingCurve')}
              </div>
            )}
            <div ref={chartRef} style={{ width: '100%', height: 400 }} />
          </>
        )}
      </div>
    </div>
  )
}
