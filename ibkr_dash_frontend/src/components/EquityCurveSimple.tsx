import { useRef, useEffect, useCallback } from 'react'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EquityCurvePoint } from '@/types/charts'
import type { EquityCurveRangeKey, EquityCurveRangeOption } from '@/utils/equityCurveRange'
import { formatNumber } from '@/utils/format'

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

interface Props {
  items: EquityCurvePoint[]
  loading: boolean
  errorMessage: string
  rangeOptions: EquityCurveRangeOption[]
  selectedRange: EquityCurveRangeKey
  onSelectRange: (range: EquityCurveRangeKey) => void
}

export default function EquityCurveSimple({ items, loading, errorMessage, rangeOptions, selectedRange, onSelectRange }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

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

    chartInstance.current.setOption({
      animationDuration: 700,
      backgroundColor: 'transparent',
      grid: { top: 72, right: 72, bottom: 86, left: 28 },
      legend: { show: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(6, 12, 24, 0.96)',
        borderColor: 'rgba(129, 160, 207, 0.22)',
        borderWidth: 1,
        textStyle: { color: '#e6eefc' },
        padding: 14,
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'rgba(129, 160, 207, 0.16)' } },
        axisTick: { show: false },
        axisLabel: { color: '#6d7d9d', margin: 16 },
        splitLine: { show: false },
      },
      yAxis: [{
        type: 'value',
        position: 'right',
        axisLabel: { color: '#6d7d9d' },
        splitNumber: 4,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: 'rgba(129, 160, 207, 0.11)', type: 'dashed' } },
      }],
      dataZoom: [
        { type: 'inside', xAxisIndex: 0 },
        {
          type: 'slider', xAxisIndex: 0, height: 22, bottom: 24,
          borderColor: 'rgba(129, 160, 207, 0.08)',
          backgroundColor: 'rgba(9, 16, 29, 0.72)',
          fillerColor: 'rgba(62, 169, 255, 0.18)',
          handleStyle: { color: '#13284a', borderColor: '#56d5ff' },
          textStyle: { color: '#6d7d9d' },
        },
      ],
      series: [
        {
          name: 'Total Equity', type: 'line', smooth: 0.18, sampling: 'lttb',
          data: equityData, lineStyle: { width: 3, color: '#56d5ff' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(86, 213, 255, 0.26)' },
            { offset: 1, color: 'rgba(86, 213, 255, 0.02)' },
          ]) },
          showSymbol: false,
        },
        {
          name: 'Net P&L', type: 'line', smooth: 0.22, sampling: 'lttb',
          data: pnlData, lineStyle: { width: 2.5, color: '#b7e11d' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(183, 225, 29, 0.18)' },
            { offset: 1, color: 'rgba(183, 225, 29, 0.01)' },
          ]) },
          showSymbol: false,
        },
        {
          name: 'Net Cost', type: 'line', step: 'end',
          data: costData, lineStyle: { width: 2.5, color: '#ffb454' },
          showSymbol: false,
        },
        {
          name: 'Realized P&L', type: 'line', smooth: 0.16, sampling: 'lttb',
          data: realizedData, lineStyle: { width: 2.4, color: '#8b7cff' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 124, 255, 0.14)' },
            { offset: 1, color: 'rgba(139, 124, 255, 0.01)' },
          ]) },
          showSymbol: false,
        },
      ],
    }, true)
  }, [items])

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

  const latestPoint = items[items.length - 1] ?? null

  return (
    <div className="surface-panel" style={{ position: 'relative', overflow: 'hidden' }}>
      <div className="surface-panel__content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
          <div>
            <p className="eyebrow">Curves</p>
            <h2 className="panel-title" style={{ fontSize: '1.45rem' }}>Equity / P&L / Cost / Realized P&L</h2>
            <p className="panel-subtitle" style={{ maxWidth: '52rem' }}>
              Net P&L is calculated as total equity minus cumulative net contributions. Realized P&L is derived from historical trade records.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <span className="tag tag--accent">
              {items.length > 0 ? `${items[0].report_date} - ${items[items.length - 1].report_date}` : 'No history'}
            </span>
            <span className="tag">{items.length} daily points</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 'var(--space-4)' }}>
          {rangeOptions.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className="btn"
              style={{
                borderRadius: 999, padding: '8px 14px',
                background: selectedRange === opt.key ? 'linear-gradient(135deg, rgba(34, 99, 196, 0.96), rgba(18, 59, 128, 0.96))' : 'rgba(15, 26, 45, 0.72)',
                borderColor: selectedRange === opt.key ? 'rgba(116, 194, 255, 0.45)' : 'rgba(129, 160, 207, 0.12)',
                color: selectedRange === opt.key ? '#f4f8ff' : 'var(--color-text-secondary)',
              }}
              onClick={() => onSelectRange(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {items.length === 0 ? (
          <div className="empty-state">{errorMessage || 'No curve data available'}</div>
        ) : (
          <>
            {loading && (
              <div style={{
                position: 'absolute', inset: 0, zIndex: 3,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(5, 12, 24, 0.44)', backdropFilter: 'blur(3px)',
                color: 'var(--color-text-primary)', fontWeight: 600,
              }}>
                Updating curve...
              </div>
            )}
            <div ref={chartRef} style={{ width: '100%', height: 620, borderRadius: 24, border: '1px solid rgba(129, 160, 207, 0.1)', background: 'rgba(8, 14, 28, 0.94)' }} />
          </>
        )}
      </div>
    </div>
  )
}
