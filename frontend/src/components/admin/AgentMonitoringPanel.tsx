import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsType } from 'echarts/core'
import {
  getAgentMonitoringOverview,
  getAgentRecentLlmCalls,
  getAgentRecentToolCalls,
  getStructuredOutputRecent,
  getToolReliabilityLatest,
  runToolReliabilityProbe,
} from '@/api/accountCopilot'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import { formatLocalDateTime } from '@/utils/dateTime'
import type {
  AgentMonitoringOverviewResponse,
  AgentMonitoringStatusSummary,
  AgentRecentLlmCall,
  AgentRecentToolCall,
  AgentStructuredOutputEvent,
  CopilotToolProbeResult,
  CopilotToolReliabilityLatestResponse,
  CopilotToolReliabilityProbeResponse,
} from '@/types/accountCopilot'

echarts.use([LineChart, BarChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

type ProbeKind = 'mcp' | 'ibkr'
type CallTypeFilter = 'all' | 'mcp' | 'ibkr' | 'llm'

const agentOptions = [
  { label: '全部 Agent', value: '' },
  { label: 'Trade Decision', value: 'trade_decision' },
  { label: 'Account Copilot', value: 'account_copilot' },
  { label: 'Trade Review', value: 'trade_review' },
  { label: 'Daily Review', value: 'daily_review' },
]
const typeOptions: { label: string; value: CallTypeFilter }[] = [
  { label: '全部', value: 'all' },
  { label: 'MCP', value: 'mcp' },
  { label: 'IBKR', value: 'ibkr' },
  { label: 'LLM', value: 'llm' },
]
const limitOptions = [50, 100, 200, 500]

const SENSITIVE_KEYWORDS = ['api_key', 'apikey', 'cookie', 'authorization', 'secret', 'password', 'access_token', 'refresh_token']
const SENSITIVE_VALUE_PATTERN = /(bearer\s+[a-z0-9._~+/-]+|sk-[a-z0-9_-]+|api[_-]?key\s*[:=]\s*[^,\s]+)/gi

const METRIC_LABELS: Record<string, string> = {
  latency_ms: '调用耗时',
  rolling_success_rate_10: '最近10次成功率',
  missing_fields_count: '缺失字段数',
  total_tokens: 'Token 消耗',
  rolling_repair_rate_10: '最近10次修复率',
  rolling_fallback_rate_10: '最近10次兜底率',
  repair_attempts: '修复次数',
}

const tooltipBase = {
  backgroundColor: 'rgba(8, 13, 24, 0.96)',
  borderColor: 'rgba(129, 160, 207, 0.22)',
  textStyle: { color: '#dbeafe' },
}

const AXIS_STYLE = { color: '#9fb2d1' }
const SPLIT_LINE = { lineStyle: { color: 'rgba(129, 160, 207, 0.12)' } }
const AXIS_LINE = { lineStyle: { color: 'rgba(159, 178, 209, 0.24)' } }

// --- Utility functions ---

function fmtOk(v: unknown): string {
  return v === true ? '成功' : v === false ? '失败' : '--'
}
function fmtBool(v: unknown): string {
  return v === true ? '是' : v === false ? '否' : '--'
}
function roundPct(value: number | null | undefined): number {
  return Number(((value ?? 0) * 100).toFixed(1))
}
function formatPct(value: number | null | undefined): string {
  return `${roundPct(value).toFixed(1)}%`
}
function formatMs(value: number | null | undefined): string {
  const ms = Math.round(value ?? 0)
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}
function formatNumber(value: number | null | undefined): string {
  return new Intl.NumberFormat('zh-CN').format(Math.round(value ?? 0))
}
function formatTime(value: string | null | undefined): string {
  return formatLocalDateTime(value) || '--'
}
function timestamp(value: string): number {
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? 0 : time
}
function statusLabel(status: string | undefined): string {
  switch (status) {
    case 'healthy': return '正常'
    case 'degraded': return '降级'
    case 'down': return '异常'
    default: return '暂无数据'
  }
}
function statusTagClass(status: string | undefined): string {
  switch (status) {
    case 'healthy': return 'tag tag--positive'
    case 'degraded': return 'tag tag--warning'
    case 'down': return 'tag tag--danger'
    default: return 'tag'
  }
}
function getLegacySummaryMetric(summary: AgentMonitoringStatusSummary | undefined, metric: string): number {
  if (!summary) return 0
  const requested = `${metric}_24h`
  const value = (summary as unknown as Record<string, unknown>)[requested] ?? 0
  return typeof value === 'number' ? value : 0
}
function isSensitiveKey(key: string): boolean {
  const lower = key.toLowerCase()
  return SENSITIVE_KEYWORDS.some((keyword) => lower === keyword || lower.includes(keyword))
}
function sanitizeText(value: string | null | undefined): string {
  if (!value) return ''
  let sanitized = value.replace(SENSITIVE_VALUE_PATTERN, '***REDACTED***')
  SENSITIVE_KEYWORDS.forEach((keyword) => {
    const pattern = new RegExp(`(${keyword}\\s*[:=]\\s*)[^,;\\s]+`, 'gi')
    sanitized = sanitized.replace(pattern, '$1***REDACTED***')
  })
  return sanitized
}
function truncateText(value: string | null | undefined, maxLength = 120): string {
  const sanitized = sanitizeText(value)
  return sanitized.length > maxLength ? `${sanitized.slice(0, maxLength)}...` : sanitized
}
function sanitizeObject(obj: Record<string, any> | null | undefined): Record<string, any> {
  if (!obj) return {}
  const out: Record<string, any> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (isSensitiveKey(key)) {
      out[key] = '***REDACTED***'
    } else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      out[key] = sanitizeObject(value as Record<string, any>)
    } else if (typeof value === 'string') {
      out[key] = sanitizeText(value)
    } else {
      out[key] = value
    }
  }
  return out
}
function emptyHint(kind: string): string {
  return `当前筛选条件下没有${kind}调用记录。可以点击一键检测 MCP / IBKR，或先运行一次 AI 决策任务后刷新。`
}
function percentile(values: number[], ratio: number): number {
  const sorted = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b)
  if (!sorted.length) return 0
  const index = Math.min(sorted.length - 1, Math.ceil(sorted.length * ratio) - 1)
  return sorted[index]
}
function statusFromSuccessRate(successRate: number, total: number): string {
  if (total <= 0) return 'unknown'
  if (successRate >= 0.95) return 'healthy'
  if (successRate >= 0.8) return 'degraded'
  return 'down'
}
function summarizeRecent(items: Array<{ ok: boolean; latency_ms: number; rolling_success_rate_10?: number }>): { count: number; successRate: number; p95: number; status: string } {
  const count = items.length
  const last = items[count - 1]
  const successRate = last?.rolling_success_rate_10 ?? (count ? items.filter((item) => item.ok).length / count : 0)
  const p95 = percentile(items.map((item) => item.latency_ms), 0.95)
  return { count, successRate, p95, status: statusFromSuccessRate(successRate, count) }
}

// --- Main Component ---

export default function AgentMonitoringPanel() {
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [probeMessage, setProbeMessage] = useState('')
  const [probing, setProbing] = useState<ProbeKind | null>(null)
  const [selectedAgent, setSelectedAgent] = useState('')
  const [selectedType, setSelectedType] = useState<CallTypeFilter>('all')
  const [selectedLimit, setSelectedLimit] = useState(100)
  const [overview, setOverview] = useState<AgentMonitoringOverviewResponse | null>(null)
  const [toolCalls, setToolCalls] = useState<AgentRecentToolCall[]>([])
  const [llmCalls, setLlmCalls] = useState<AgentRecentLlmCall[]>([])
  const [soEvents, setSoEvents] = useState<AgentStructuredOutputEvent[]>([])
  const [latestProbe, setLatestProbe] = useState<CopilotToolReliabilityLatestResponse | CopilotToolReliabilityProbeResponse | null>(null)
  const [showProbeDetails, setShowProbeDetails] = useState(false)
  const [expandedFailure, setExpandedFailure] = useState<string | null>(null)
  const [expandedProbeRow, setExpandedProbeRow] = useState<string | null>(null)

  // Chart refs
  const ibkrChartRef = useRef<HTMLDivElement>(null)
  const mcpChartRef = useRef<HTMLDivElement>(null)
  const llmChartRef = useRef<HTMLDivElement>(null)
  const llmTokenChartRef = useRef<HTMLDivElement>(null)
  const soChartRef = useRef<HTMLDivElement>(null)

  // Chart instances (mutable, not state)
  const chartsRef = useRef<{
    ibkr: EChartsType | null
    mcp: EChartsType | null
    llm: EChartsType | null
    llmToken: EChartsType | null
    so: EChartsType | null
    resizeObserver: ResizeObserver | null
  }>({ ibkr: null, mcp: null, llm: null, llmToken: null, so: null, resizeObserver: null })

  // Computed values
  const ibkrCalls = useMemo(() => toolCalls.filter((item) => item.tool_domain === 'ibkr'), [toolCalls])
  const mcpCalls = useMemo(() => toolCalls.filter((item) => item.tool_domain === 'longbridge'), [toolCalls])
  const soFailures = useMemo(() =>
    soEvents.filter((e) => !e.ok || e.repaired || e.fallback_used).slice(0, 50),
  [soEvents])
  const visibleProbeResults = useMemo(() =>
    (latestProbe?.results ?? []).filter((row) => ['fail', 'partial', 'skipped'].includes(row.status)),
  [latestProbe])
  const hasVisibleProbeResults = useMemo(() => visibleProbeResults.length > 0, [visibleProbeResults])

  const statusCards = useMemo(() => [
    {
      key: 'ibkr',
      title: 'IBKR 工具',
      icon: 'pi pi-database',
      summary: overview?.ibkr,
      recent: summarizeRecent(ibkrCalls),
    },
    {
      key: 'mcp',
      title: 'MCP 工具',
      icon: 'pi pi-link',
      summary: overview?.longbridge,
      recent: summarizeRecent(mcpCalls),
    },
    {
      key: 'llm',
      title: 'LLM',
      icon: 'pi pi-sparkles',
      summary: overview?.llm,
      recent: summarizeRecent(llmCalls),
      models: Array.from(new Set(llmCalls.map((item) => item.model).filter(Boolean))).slice(0, 6),
    },
  ], [overview, ibkrCalls, mcpCalls, llmCalls])

  const recentFailures = useMemo(() => {
    const toolRows = toolCalls
      .filter((item) => item.ok === false || item.empty_result || item.compact_ok === false || item.missing_fields_count > 0)
      .map((item) => ({
        key: `tool:${item.id}`,
        created_at: item.created_at,
        kind: 'tool' as const,
        agent_name: item.agent_name,
        node_name: item.node_name,
        name: item.tool_name,
        domain: item.tool_domain,
        error_code: item.error_code || (item.missing_fields_count > 0 ? 'PARTIAL_FIELDS' : item.empty_result ? 'EMPTY_RESULT' : ''),
        error_message: item.error_message || (item.missing_fields_count > 0 ? `缺少字段 ${item.missing_fields_count} 个` : ''),
        latency_ms: item.latency_ms,
        run_id: item.run_id,
        task_id: item.task_id,
        partial: item.ok && item.missing_fields_count > 0,
      }))
    const llmRows = llmCalls
      .filter((item) => item.ok === false)
      .map((item) => ({
        key: `llm:${item.id}`,
        created_at: item.created_at,
        kind: 'llm' as const,
        agent_name: item.agent_name,
        node_name: item.node_name,
        name: item.model,
        domain: 'llm',
        error_code: item.error_code || '',
        error_message: item.error_message || '',
        latency_ms: item.latency_ms,
        run_id: item.run_id,
        task_id: item.task_id,
        partial: false,
      }))
    return [...toolRows, ...llmRows]
      .sort((a, b) => timestamp(b.created_at) - timestamp(a.created_at))
      .slice(0, 80)
  }, [toolCalls, llmCalls])

  // Chart management functions
  const ensureCharts = useCallback(() => {
    const c = chartsRef.current

    // Dispose stale instances
    if (c.ibkr && (!ibkrChartRef.current || c.ibkr.getDom() !== ibkrChartRef.current)) { c.ibkr.dispose(); c.ibkr = null }
    if (c.mcp && (!mcpChartRef.current || c.mcp.getDom() !== mcpChartRef.current)) { c.mcp.dispose(); c.mcp = null }
    if (c.llm && (!llmChartRef.current || c.llm.getDom() !== llmChartRef.current)) { c.llm.dispose(); c.llm = null }
    if (c.llmToken && (!llmTokenChartRef.current || c.llmToken.getDom() !== llmTokenChartRef.current)) { c.llmToken.dispose(); c.llmToken = null }
    if (c.so && (!soChartRef.current || c.so.getDom() !== soChartRef.current)) { c.so.dispose(); c.so = null }

    if (!c.ibkr && ibkrChartRef.current) c.ibkr = echarts.init(ibkrChartRef.current, undefined, { renderer: 'canvas' })
    if (!c.mcp && mcpChartRef.current) c.mcp = echarts.init(mcpChartRef.current, undefined, { renderer: 'canvas' })
    if (!c.llm && llmChartRef.current) c.llm = echarts.init(llmChartRef.current, undefined, { renderer: 'canvas' })
    if (!c.llmToken && llmTokenChartRef.current) c.llmToken = echarts.init(llmTokenChartRef.current, undefined, { renderer: 'canvas' })
    if (!c.so && soChartRef.current) c.so = echarts.init(soChartRef.current, undefined, { renderer: 'canvas' })

    if (!c.resizeObserver && (ibkrChartRef.current || mcpChartRef.current || llmChartRef.current || llmTokenChartRef.current || soChartRef.current)) {
      c.resizeObserver = new ResizeObserver(() => {
        c.ibkr?.resize()
        c.mcp?.resize()
        c.llm?.resize()
        c.llmToken?.resize()
        c.so?.resize()
      })
      ;[ibkrChartRef.current, mcpChartRef.current, llmChartRef.current, llmTokenChartRef.current, soChartRef.current].forEach((el) => {
        if (el) c.resizeObserver?.observe(el)
      })
    }
  }, [])

  const renderToolChart = useCallback((chart: EChartsType | null, calls: AgentRecentToolCall[], _title: string) => {
    if (!chart) return
    const labels = calls.map((_, i) => `#${i + 1}`)
    chart.setOption({
      color: ['#60a5fa', '#22c55e', '#f59e0b', '#ef4444'],
      backgroundColor: 'transparent',
      legend: { top: 6, right: 0, textStyle: { color: '#9fb2d1' }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 52, right: 60, top: 42, bottom: 42 },
      tooltip: {
        trigger: 'axis',
        ...tooltipBase,
        formatter: (params: any) => {
          const rows = Array.isArray(params) ? params : [params]
          const idx = rows[0]?.dataIndex ?? 0
          const p = calls[idx]
          if (!p) return '暂无调用'
          return [
            `${rows[0]?.axisValue || ''} · ${formatTime(p.created_at)}`,
            `Agent: ${p.agent_name}　节点: ${p.node_name}`,
            `工具: ${p.tool_name}`,
            `是否成功: ${fmtOk(p.ok)}　调用耗时: ${formatMs(p.latency_ms)}`,
            `最近10次成功率: ${formatPct(p.rolling_success_rate_10)} (${p.rolling_window_size})`,
            `最近10次失败率: ${formatPct(p.rolling_failure_rate_10)}`,
            `是否空结果: ${fmtBool(p.empty_result)}`,
            `原始调用成功: ${fmtOk(p.raw_ok)}　压缩解析成功: ${fmtOk(p.compact_ok)}`,
            `已解析字段: ${p.parsed_fields_count}　缺失字段: ${p.missing_fields_count}`,
            p.error_code ? `错误码: ${p.error_code}` : '',
            p.error_message ? `错误信息: ${truncateText(p.error_message, 160)}` : '',
          ].filter(Boolean).join('<br/>')
        },
      },
      xAxis: { type: 'category', axisLine: AXIS_LINE, axisTick: { show: false }, axisLabel: AXIS_STYLE, data: labels },
      yAxis: [
        { type: 'value', min: 0, name: '耗时 / 缺失字段', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { formatter: '{value}', ...AXIS_STYLE }, splitLine: SPLIT_LINE },
        { type: 'value', min: 0, max: 100, name: '成功率', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { formatter: '{value}%', ...AXIS_STYLE }, splitLine: { show: false } },
      ],
      series: [
        { name: METRIC_LABELS.latency_ms, type: 'line', yAxisIndex: 0, smooth: true, data: calls.map((c) => c.latency_ms) },
        { name: METRIC_LABELS.rolling_success_rate_10, type: 'line', yAxisIndex: 1, smooth: true, data: calls.map((c) => roundPct(c.rolling_success_rate_10)) },
        { name: METRIC_LABELS.missing_fields_count, type: 'bar', yAxisIndex: 0, barMaxWidth: 16, data: calls.map((c) => c.missing_fields_count) },
        { name: '异常点', type: 'scatter', yAxisIndex: 0, symbolSize: 9, data: calls.map((c) => (c.ok === false || c.empty_result || c.compact_ok === false ? c.latency_ms : null)) },
      ],
    }, true)
  }, [])

  const renderLlmStabilityChart = useCallback((calls: AgentRecentLlmCall[]) => {
    const c = chartsRef.current
    if (!c.llm) return
    const labels = calls.map((_, i) => `#${i + 1}`)
    c.llm.setOption({
      color: ['#60a5fa', '#22c55e', '#ef4444'],
      backgroundColor: 'transparent',
      legend: { top: 6, right: 0, textStyle: { color: '#9fb2d1' }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 52, right: 60, top: 42, bottom: 42 },
      tooltip: {
        trigger: 'axis',
        ...tooltipBase,
        formatter: (params: any) => {
          const rows = Array.isArray(params) ? params : [params]
          const idx = rows[0]?.dataIndex ?? 0
          const p = calls[idx]
          if (!p) return '暂无调用'
          return [
            `${rows[0]?.axisValue || ''} · ${formatTime(p.created_at)}`,
            `Agent: ${p.agent_name}　节点: ${p.node_name}`,
            `服务商: ${p.provider}　模型: ${p.model}`,
            `调用类型: ${p.call_type}`,
            `是否成功: ${fmtOk(p.ok)}　调用耗时: ${formatMs(p.latency_ms)}`,
            `输入 Token: ${formatNumber(p.prompt_tokens)}　输出 Token: ${formatNumber(p.completion_tokens)}`,
            `最近10次成功率: ${formatPct(p.rolling_success_rate_10)} (${p.rolling_window_size})`,
            p.error_code ? `错误码: ${p.error_code}` : '',
            p.error_message ? `错误信息: ${truncateText(p.error_message, 160)}` : '',
          ].filter(Boolean).join('<br/>')
        },
      },
      xAxis: { type: 'category', axisLine: AXIS_LINE, axisTick: { show: false }, axisLabel: AXIS_STYLE, data: labels },
      yAxis: [
        { type: 'value', min: 0, name: '耗时 (ms)', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { formatter: '{value}', ...AXIS_STYLE }, splitLine: SPLIT_LINE },
        { type: 'value', min: 0, max: 100, name: '成功率', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { formatter: '{value}%', ...AXIS_STYLE }, splitLine: { show: false } },
      ],
      series: [
        { name: METRIC_LABELS.latency_ms, type: 'line', yAxisIndex: 0, smooth: true, data: calls.map((c) => c.latency_ms) },
        { name: METRIC_LABELS.rolling_success_rate_10, type: 'line', yAxisIndex: 1, smooth: true, data: calls.map((c) => roundPct(c.rolling_success_rate_10)) },
        { name: '失败点', type: 'scatter', yAxisIndex: 0, symbolSize: 9, data: calls.map((c) => (c.ok === false ? c.latency_ms : null)) },
      ],
    }, true)
  }, [])

  const renderLlmTokenChart = useCallback((calls: AgentRecentLlmCall[]) => {
    const c = chartsRef.current
    if (!c.llmToken) return
    const labels = calls.map((_, i) => `#${i + 1}`)
    c.llmToken.setOption({
      color: ['#a78bfa', '#60a5fa'],
      backgroundColor: 'transparent',
      legend: { top: 6, right: 0, textStyle: { color: '#9fb2d1' }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 60, right: 24, top: 42, bottom: 42 },
      tooltip: {
        trigger: 'axis',
        ...tooltipBase,
        formatter: (params: any) => {
          const rows = Array.isArray(params) ? params : [params]
          const idx = rows[0]?.dataIndex ?? 0
          const p = calls[idx]
          if (!p) return '暂无调用'
          return [
            `${rows[0]?.axisValue || ''} · ${formatTime(p.created_at)}`,
            `模型: ${p.model}`,
            `输入 Token: ${formatNumber(p.prompt_tokens)}`,
            `输出 Token: ${formatNumber(p.completion_tokens)}`,
            `总 Token: ${formatNumber(p.total_tokens)}`,
          ].join('<br/>')
        },
      },
      xAxis: { type: 'category', axisLine: AXIS_LINE, axisTick: { show: false }, axisLabel: AXIS_STYLE, data: labels },
      yAxis: [
        { type: 'value', min: 0, name: 'Token 数', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { ...AXIS_STYLE }, splitLine: SPLIT_LINE },
      ],
      series: [
        { name: '输入 Token', type: 'bar', stack: 'tokens', barMaxWidth: 20, data: calls.map((c) => c.prompt_tokens) },
        { name: '输出 Token', type: 'bar', stack: 'tokens', barMaxWidth: 20, data: calls.map((c) => c.completion_tokens) },
      ],
    }, true)
  }, [])

  const renderSoChart = useCallback((events: AgentStructuredOutputEvent[]) => {
    const c = chartsRef.current
    if (!c.so) return
    const labels = events.map((_, i) => `#${i + 1}`)
    c.so.setOption({
      color: ['#60a5fa', '#22c55e', '#f59e0b', '#ef4444', '#a78bfa'],
      backgroundColor: 'transparent',
      legend: { top: 6, right: 0, textStyle: { color: '#9fb2d1' }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 52, right: 60, top: 42, bottom: 42 },
      tooltip: {
        trigger: 'axis',
        ...tooltipBase,
        formatter: (params: any) => {
          const rows = Array.isArray(params) ? params : [params]
          const idx = rows[0]?.dataIndex ?? 0
          const p = events[idx]
          if (!p) return '暂无记录'
          return [
            `${rows[0]?.axisValue || ''} · ${formatTime(p.created_at)}`,
            `输出契约: ${p.contract_name}`,
            `Agent: ${p.agent_name}　节点: ${p.node_name}`,
            `是否成功: ${fmtOk(p.ok)}`,
            `是否修复: ${fmtBool(p.repaired)}${p.repaired ? ` (${p.repair_attempts} 次)` : ''}`,
            `是否兜底: ${fmtBool(p.fallback_used)}`,
            `Schema 校验: ${fmtOk(p.schema_validation_passed)}`,
            `最近10次成功率: ${formatPct(p.rolling_success_rate_10)}`,
            `最近10次修复率: ${formatPct(p.rolling_repair_rate_10)}`,
            `最近10次兜底率: ${formatPct(p.rolling_fallback_rate_10)}`,
            p.error_code ? `错误码: ${p.error_code}` : '',
            p.error_message ? `错误信息: ${truncateText(p.error_message, 160)}` : '',
            `run_id: ${p.run_id || '--'}`,
            `task_id: ${p.task_id || '--'}`,
          ].filter(Boolean).join('<br/>')
        },
      },
      xAxis: { type: 'category', axisLine: AXIS_LINE, axisTick: { show: false }, axisLabel: AXIS_STYLE, data: labels },
      yAxis: [
        { type: 'value', min: 0, max: 100, name: '比例 (%)', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { formatter: '{value}%', ...AXIS_STYLE }, splitLine: SPLIT_LINE },
        { type: 'value', min: 0, name: '次数', nameTextStyle: { color: '#9fb2d1', fontSize: 11 }, nameGap: 8, axisLabel: { ...AXIS_STYLE }, splitLine: { show: false } },
      ],
      series: [
        { name: METRIC_LABELS.rolling_success_rate_10, type: 'line', yAxisIndex: 0, smooth: true, data: events.map((e) => roundPct(e.rolling_success_rate_10)) },
        { name: METRIC_LABELS.rolling_repair_rate_10, type: 'line', yAxisIndex: 0, smooth: true, data: events.map((e) => roundPct(e.rolling_repair_rate_10)) },
        { name: METRIC_LABELS.rolling_fallback_rate_10, type: 'line', yAxisIndex: 0, smooth: true, data: events.map((e) => roundPct(e.rolling_fallback_rate_10)) },
        { name: METRIC_LABELS.repair_attempts, type: 'bar', yAxisIndex: 1, barMaxWidth: 12, data: events.map((e) => e.repair_attempts) },
        { name: '输出状态', type: 'scatter', yAxisIndex: 1, symbolSize: 10, data: events.map((e) => { if (!e.ok) return 1; if (e.fallback_used) return 0.8; if (e.repaired) return 0.5; return 0 }) },
      ],
    }, true)
  }, [])

  const renderCharts = useCallback(() => {
    ensureCharts()
    const c = chartsRef.current
    if (selectedType === 'llm') {
      renderToolChart(c.ibkr, [], 'IBKR 工具调用稳定性')
      renderToolChart(c.mcp, [], 'Longbridge MCP 公开数据工具稳定性')
    } else {
      renderToolChart(c.ibkr, selectedType === 'mcp' ? [] : ibkrCalls, 'IBKR 工具调用稳定性')
      renderToolChart(c.mcp, selectedType === 'ibkr' ? [] : mcpCalls, 'Longbridge MCP 公开数据工具稳定性')
    }
    const llmData = selectedType === 'mcp' || selectedType === 'ibkr' ? [] : llmCalls
    renderLlmStabilityChart(llmData)
    renderLlmTokenChart(llmData)
    renderSoChart(soEvents)
  }, [selectedType, ibkrCalls, mcpCalls, llmCalls, soEvents, ensureCharts, renderToolChart, renderLlmStabilityChart, renderLlmTokenChart, renderSoChart])

  // Load data
  const loadAll = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const agentName = selectedAgent || undefined
      const [overviewResponse, toolResponse, llmResponse, latestResponse, soResponse] = await Promise.all([
        getAgentMonitoringOverview({ hours: 24, bucket: '1h' }),
        getAgentRecentToolCalls({ limit: selectedLimit, agent_name: agentName }),
        getAgentRecentLlmCalls({ limit: selectedLimit, agent_name: agentName }),
        getToolReliabilityLatest(),
        getStructuredOutputRecent({ limit: selectedLimit, agent_name: agentName || undefined }).catch(() => ({ items: [] })),
      ])
      setOverview(overviewResponse)
      setToolCalls(toolResponse.items || [])
      setLlmCalls(llmResponse.items || [])
      setLatestProbe(latestResponse)
      setSoEvents(soResponse.items || [])
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '加载 Agent 监控数据失败')
    } finally {
      setLoading(false)
    }
  }, [selectedAgent, selectedLimit])

  // Run probe
  const runOneClickProbe = useCallback(async (kind: ProbeKind) => {
    setProbing(kind)
    setProbeMessage('')
    setErrorMessage('')
    try {
      const response = await runToolReliabilityProbe({
        include_live: true,
        include_longbridge: kind === 'mcp',
        include_ibkr: kind === 'ibkr',
        include_agent_eval: false,
        symbol: 'AMD.US',
        keyword: 'AMD',
        max_tools: 20,
      })
      setLatestProbe(response)
      setProbeMessage([
        `${kind === 'mcp' ? 'MCP' : 'IBKR'} 检测完成`,
        `total ${response.total}`,
        `pass ${response.pass}`,
        `fail ${response.fail}`,
        `skipped ${response.skipped}`,
        `成功率 ${formatPct(response.success_rate)}`,
        '检测结果已写入监控数据。',
      ].join(' · '))
      await loadAll()
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '运行检测失败')
    } finally {
      setProbing(null)
    }
  }, [loadAll])

  // Effects
  useEffect(() => {
    void loadAll()
  }, [loadAll])

  // Render charts after data loads
  useEffect(() => {
    if (!loading) {
      requestAnimationFrame(() => {
        ensureCharts()
        renderCharts()
      })
    }
  }, [loading, ensureCharts, renderCharts])

  // Re-render charts when filter changes
  useEffect(() => {
    renderCharts()
  }, [renderCharts])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      const c = chartsRef.current
      c.resizeObserver?.disconnect()
      c.ibkr?.dispose()
      c.mcp?.dispose()
      c.llm?.dispose()
      c.llmToken?.dispose()
      c.so?.dispose()
    }
  }, [])

  function toggleFailure(row: { key: string }) {
    setExpandedFailure((prev) => prev === row.key ? null : row.key)
  }

  function toggleProbeRow(row: CopilotToolProbeResult) {
    setExpandedProbeRow((prev) => prev === row.id ? null : row.id)
  }

  function probeStatusClass(status: string): string {
    switch (status) {
      case 'pass': return 'tag tag--positive'
      case 'fail': return 'tag tag--danger'
      case 'partial': return 'tag tag--warning'
      default: return 'tag'
    }
  }

  if (loading) return <LoadingBlock />

  return (
    <section style={{ display: 'grid', gap: 'var(--space-4)' }}>
      {errorMessage && <ErrorBlock message={errorMessage} />}

      {/* Toolbar */}
      <section className="surface-panel">
        <div className="surface-panel__content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <p className="eyebrow">RECENT CALLS</p>
            <h3 className="panel-title">运行监控</h3>
            <p className="panel-subtitle">每个点代表一次真实调用；成功率为最近 10 次滚动值。</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'end', justifyContent: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
            <label style={{ display: 'grid', gap: 5, color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>
              Agent
              <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)} style={selectStyle}>
                {agentOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label style={{ display: 'grid', gap: 5, color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>
              类型
              <select value={selectedType} onChange={(e) => setSelectedType(e.target.value as CallTypeFilter)} style={selectStyle}>
                {typeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label style={{ display: 'grid', gap: 5, color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>
              Limit
              <select value={selectedLimit} onChange={(e) => setSelectedLimit(Number(e.target.value))} style={selectStyle}>
                {limitOptions.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </label>
            <button className="btn btn--secondary" onClick={() => void loadAll()}>刷新</button>
          </div>
        </div>
      </section>

      {/* Status Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14 }}>
        {statusCards.map((card) => (
          <article key={card.key} style={{ display: 'grid', gap: 16, padding: 18, border: `1px solid ${card.recent.status === 'healthy' ? 'rgba(34,197,94,0.35)' : card.recent.status === 'degraded' ? 'rgba(245,158,11,0.38)' : card.recent.status === 'down' ? 'rgba(239,68,68,0.42)' : 'rgba(129,160,207,0.16)'}`, borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.62)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 42, height: 42, borderRadius: 'var(--radius-sm)', background: 'rgba(129,160,207,0.13)', color: '#bfdbfe' }}>
                <i className={card.icon} />
              </span>
              <div>
                <h3 style={{ margin: '0 0 6px', fontSize: '1rem' }}>{card.title}</h3>
                <span className={statusTagClass(card.recent.status)}>{statusLabel(card.recent.status)}</span>
              </div>
            </div>
            <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10, margin: 0 }}>
              <div>
                <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>最近 10 次成功率</dt>
                <dd style={{ margin: '5px 0 0', fontWeight: 700 }}>{formatPct(card.recent.successRate)}</dd>
              </div>
              <div>
                <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>当前列表调用数</dt>
                <dd style={{ margin: '5px 0 0', fontWeight: 700 }}>{card.recent.count}</dd>
              </div>
              <div>
                <dt style={{ color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>P95 耗时</dt>
                <dd style={{ margin: '5px 0 0', fontWeight: 700 }}>{formatMs(card.recent.p95 || getLegacySummaryMetric(card.summary, 'p95_latency_ms'))}</dd>
              </div>
            </dl>
            {'models' in card && card.models?.length ? (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {card.models.map((model) => (
                  <span key={model} style={{ padding: '4px 8px', borderRadius: 'var(--radius-sm)', background: 'rgba(129,160,207,0.12)', color: 'var(--color-text-secondary)', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.74rem' }}>{model}</span>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </section>

      {/* Probe Actions */}
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <h3 className="panel-title">一键检测</h3>
              <p className="panel-subtitle">检测只会调用只读工具，不会下单、撤单、转账或修改账户。</p>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button className="btn btn--primary" disabled={probing !== null} onClick={() => void runOneClickProbe('mcp')}>
                {probing === 'mcp' ? '检测中...' : '一键检测 MCP'}
              </button>
              <button className="btn btn--secondary" disabled={probing !== null} onClick={() => void runOneClickProbe('ibkr')}>
                {probing === 'ibkr' ? '检测中...' : '一键检测 IBKR'}
              </button>
            </div>
          </div>
          {probeMessage && <p style={{ margin: '12px 0 0', padding: '10px 12px', border: '1px solid rgba(34,197,94,0.22)', borderRadius: 'var(--radius-sm)', background: 'rgba(20,83,45,0.18)', color: '#bbf7d0' }}>{probeMessage}</p>}
        </div>
      </section>

      {/* Charts */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 14 }}>
        {(selectedType === 'all' || selectedType === 'ibkr') && (
          <article style={{ position: 'relative', minHeight: 380, border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.54)', padding: 14 }}>
            <h4 style={{ margin: '0 0 2px', fontSize: '0.92rem', fontWeight: 600 }}>IBKR 工具调用稳定性</h4>
            <p style={{ margin: '0 0 8px', fontSize: '0.72rem', color: 'var(--color-text-tertiary)', lineHeight: 1.4 }}>观察账户、持仓、交易等 IBKR 只读工具调用是否成功、耗时是否异常、返回字段是否完整。</p>
            {!ibkrCalls.length && <div style={{ position: 'absolute', inset: '108px 28px auto', zIndex: 1, display: 'flex', justifyContent: 'center', textAlign: 'center', color: 'var(--color-text-secondary)', pointerEvents: 'none' }}>{emptyHint(' IBKR 工具')}</div>}
            <div ref={ibkrChartRef} style={{ width: '100%', height: 310 }} />
          </article>
        )}
        {(selectedType === 'all' || selectedType === 'mcp') && (
          <article style={{ position: 'relative', minHeight: 380, border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.54)', padding: 14 }}>
            <h4 style={{ margin: '0 0 2px', fontSize: '0.92rem', fontWeight: 600 }}>Longbridge MCP 公开数据工具稳定性</h4>
            <p style={{ margin: '0 0 8px', fontSize: '0.72rem', color: 'var(--color-text-tertiary)', lineHeight: 1.4 }}>观察行情、新闻、财报等公开市场数据工具调用是否成功、是否返回空结果、耗时是否异常。</p>
            {!mcpCalls.length && <div style={{ position: 'absolute', inset: '108px 28px auto', zIndex: 1, display: 'flex', justifyContent: 'center', textAlign: 'center', color: 'var(--color-text-secondary)', pointerEvents: 'none' }}>{emptyHint(' MCP 工具')}</div>}
            <div ref={mcpChartRef} style={{ width: '100%', height: 310 }} />
          </article>
        )}
        {(selectedType === 'all' || selectedType === 'llm') && (
          <article style={{ position: 'relative', minHeight: 380, border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.54)', padding: 14, gridColumn: '1 / -1' }}>
            <h4 style={{ margin: '0 0 2px', fontSize: '0.92rem', fontWeight: 600 }}>LLM 模型调用稳定性</h4>
            <p style={{ margin: '0 0 8px', fontSize: '0.72rem', color: 'var(--color-text-tertiary)', lineHeight: 1.4 }}>观察模型调用是否成功、耗时是否异常、失败点是否集中出现。</p>
            {!llmCalls.length && <div style={{ position: 'absolute', inset: '108px 28px auto', zIndex: 1, display: 'flex', justifyContent: 'center', textAlign: 'center', color: 'var(--color-text-secondary)', pointerEvents: 'none' }}>{emptyHint(' LLM')}</div>}
            <div ref={llmChartRef} style={{ width: '100%', height: 310 }} />
          </article>
        )}
        {(selectedType === 'all' || selectedType === 'llm') && (
          <article style={{ position: 'relative', minHeight: 380, border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.54)', padding: 14, gridColumn: '1 / -1' }}>
            <h4 style={{ margin: '0 0 2px', fontSize: '0.92rem', fontWeight: 600 }}>LLM Token 消耗</h4>
            <p style={{ margin: '0 0 8px', fontSize: '0.72rem', color: 'var(--color-text-tertiary)', lineHeight: 1.4 }}>观察每次模型调用的 Token 消耗，帮助判断成本和上下文是否异常膨胀。</p>
            {!llmCalls.length && <div style={{ position: 'absolute', inset: '108px 28px auto', zIndex: 1, display: 'flex', justifyContent: 'center', textAlign: 'center', color: 'var(--color-text-secondary)', pointerEvents: 'none' }}>{emptyHint(' LLM Token')}</div>}
            <div ref={llmTokenChartRef} style={{ width: '100%', height: 310 }} />
          </article>
        )}
      </section>

      {/* Structured Output Quality */}
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <h3 className="panel-title">结构化输出质量</h3>
              <p className="panel-subtitle">观察 LLM 输出 JSON 后，schema 校验、repair、fallback 是否稳定。</p>
            </div>
            <span className="tag">{`${soEvents.length} 条`}</span>
          </div>
          {soEvents.length > 0 ? (
            <div style={{ position: 'relative', minHeight: 380, border: '1px solid rgba(129,160,207,0.14)', borderRadius: 'var(--radius-md)', background: 'rgba(10,18,32,0.54)', padding: 14 }}>
              <div ref={soChartRef} style={{ width: '100%', height: 310 }} />
            </div>
          ) : (
            <div style={emptyStateStyle}>当前还没有结构化输出监控记录。请先运行一次 Account Copilot / AI 决策 / 每日复盘 / 交易复盘，然后刷新。</div>
          )}
        </div>
      </section>

      {/* Metric Legend */}
      <section className="surface-panel" style={{ marginTop: 4 }}>
        <div className="surface-panel__content">
          <h3 className="panel-title">指标说明</h3>
          <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px 24px', margin: 0 }}>
            {[
              ['调用耗时', '单次工具或模型调用花费的时间，越高说明越慢。'],
              ['最近10次成功率', '以当前点为结尾，向前最多统计10次调用的成功比例，用于观察短期稳定性。'],
              ['缺失字段数', '工具返回结果中，预期字段没有被解析到的数量，越高说明数据完整性越差。'],
              ['异常点', '调用失败、返回空结果、或解析失败的位置。'],
              ['Token 消耗', '一次模型调用使用的输入和输出 token 总数，影响成本和上下文长度。'],
              ['修复率', 'LLM 输出格式不符合 schema 后，系统尝试修复 JSON 的比例。'],
              ['兜底率', '修复失败或数据不足时，系统使用保守 fallback 结果的比例。'],
            ].map(([dt, dd]) => (
              <div key={dt}>
                <dt style={{ fontSize: '0.82rem', fontWeight: 600, marginBottom: 2 }}>{dt}</dt>
                <dd style={{ margin: 0, fontSize: '0.76rem', color: 'var(--color-text-tertiary)', lineHeight: 1.45 }}>{dd}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* SO Failures Table */}
      {soFailures.length > 0 && (
        <section className="surface-panel">
          <div className="surface-panel__content">
            <div className="section-header">
              <div>
                <h3 className="panel-title">结构化输出异常记录</h3>
                <p className="panel-subtitle">最近失败、repair 或 fallback 的结构化输出事件。</p>
              </div>
              <span className="tag tag--warning">{`${soFailures.length} 条`}</span>
            </div>
            <div className="table-shell">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem' }}>
                <thead>
                  <tr>
                    {['时间', 'Contract', 'Agent / 节点', '状态', 'Repair', 'Fallback', '错误码', 'run_id'].map((h) => (
                      <th key={h} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(129,160,207,0.12)', textAlign: 'left', color: 'var(--color-text-secondary)', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {soFailures.map((row) => (
                    <tr key={row.id}>
                      <td style={tdPad}>{formatTime(row.created_at)}</td>
                      <td style={{ ...tdPad, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.78rem' }}>{row.contract_name}</td>
                      <td style={tdPad}>{row.agent_name} / {row.node_name}</td>
                      <td style={tdPad}>
                        <span className={`tag ${row.ok ? (row.fallback_used ? 'tag--warning' : row.repaired ? '' : 'tag--positive') : 'tag--danger'}`}>
                          {row.ok ? (row.fallback_used ? 'fallback' : row.repaired ? 'repaired' : 'success') : 'failed'}
                        </span>
                      </td>
                      <td style={tdPad}>{row.repaired ? `${row.repair_attempts}次` : '--'}</td>
                      <td style={tdPad}>{row.fallback_used ? '是' : '--'}</td>
                      <td style={tdPad}>{row.error_code || '--'}</td>
                      <td style={{ ...tdPad, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.78rem' }}>{row.run_id || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* Recent Failures Table */}
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <h3 className="panel-title">最近失败与部分结果</h3>
              <p className="panel-subtitle">基于最近调用明细生成；字段缺失标记为 partial，不等同于调用失败。</p>
            </div>
            <span className="tag tag--danger">{`${recentFailures.length} 条`}</span>
          </div>
          {recentFailures.length > 0 ? (
            <div className="table-shell">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem' }}>
                <thead>
                  <tr>
                    {['时间', 'Agent / 节点', '类型', '名称', '错误码', '错误信息', '耗时', 'run / task'].map((h) => (
                      <th key={h} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(129,160,207,0.12)', textAlign: 'left', color: 'var(--color-text-secondary)', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentFailures.map((row) => (
                    <React.Fragment key={row.key}>
                      <tr style={{ cursor: 'pointer' }} onClick={() => toggleFailure(row)}>
                        <td style={tdPad}>{formatTime(row.created_at)}</td>
                        <td style={tdPad}>{row.agent_name} / {row.node_name}</td>
                        <td style={tdPad}>
                          <span className={`tag ${row.partial ? 'tag--warning' : row.kind === 'llm' ? 'tag--danger' : ''}`}>
                            {row.partial ? 'partial' : row.kind}
                          </span>
                        </td>
                        <td style={{ ...tdPad, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.78rem' }}>{row.name}</td>
                        <td style={tdPad}>{row.error_code || '--'}</td>
                        <td style={tdPad}>{truncateText(row.error_message) || '--'}</td>
                        <td style={tdPad}>{formatMs(row.latency_ms)}</td>
                        <td style={{ ...tdPad, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.78rem' }}>{row.run_id || '--'}<br />{row.task_id || '--'}</td>
                      </tr>
                      {expandedFailure === row.key && (
                        <tr>
                          <td colSpan={8} style={{ padding: 0 }}>
                            <pre style={{ maxHeight: 280, overflow: 'auto', margin: '8px 0', padding: 12, border: '1px solid rgba(129,160,207,0.12)', borderRadius: 'var(--radius-sm)', background: 'rgba(2,6,23,0.5)', color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap' }}>
                              {sanitizeText(row.error_message) || '无错误详情'}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={emptyStateStyle}>当前筛选条件下没有失败或部分结果。</div>
          )}
        </div>
      </section>

      {/* Probe Details */}
      <section className="surface-panel">
        <div className="surface-panel__content">
          <button
            type="button"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, minHeight: 36, border: '1px solid rgba(129,160,207,0.18)', borderRadius: 'var(--radius-sm)', background: 'rgba(10,18,32,0.5)', color: 'var(--color-text-secondary)', cursor: 'pointer', font: 'inherit', padding: '0 12px' }}
            onClick={() => setShowProbeDetails((prev) => !prev)}
          >
            <i className={showProbeDetails ? 'pi pi-chevron-down' : 'pi pi-chevron-right'} />
            最近主动检测明细
          </button>

          {showProbeDetails && (
            <div style={{ marginTop: 14 }}>
              {hasVisibleProbeResults ? (
                <div className="table-shell">
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem' }}>
                    <thead>
                      <tr>
                        {['Tool', 'Domain', 'Status', 'Latency', 'Error Code', 'Created At'].map((h) => (
                          <th key={h} style={{ padding: '10px 12px', borderBottom: '1px solid rgba(129,160,207,0.12)', textAlign: 'left', color: 'var(--color-text-secondary)', fontWeight: 600 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {visibleProbeResults.map((row) => (
                        <React.Fragment key={row.id}>
                          <tr style={{ cursor: 'pointer' }} onClick={() => toggleProbeRow(row)}>
                            <td style={{ ...tdPad, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.78rem' }}>{row.tool_name}</td>
                            <td style={tdPad}>{row.tool_domain}</td>
                            <td style={tdPad}><span className={probeStatusClass(row.status)}>{row.status.toUpperCase()}</span></td>
                            <td style={tdPad}>{formatMs(row.latency_ms)}</td>
                            <td style={tdPad}>{row.error_code || '--'}</td>
                            <td style={tdPad}>{formatTime(row.created_at)}</td>
                          </tr>
                          {expandedProbeRow === row.id && (
                            <tr>
                              <td colSpan={6} style={{ padding: 0 }}>
                                <div style={{ padding: 12 }}>
                                  {row.error_message && (
                                    <div>
                                      <strong>Error Message</strong>
                                      <pre style={preStyle}>{sanitizeText(row.error_message)}</pre>
                                    </div>
                                  )}
                                  <div>
                                    <strong>Arguments Preview</strong>
                                    <pre style={preStyle}>{JSON.stringify(sanitizeObject(row.arguments_preview), null, 2)}</pre>
                                  </div>
                                  <div>
                                    <strong>Metadata</strong>
                                    <pre style={preStyle}>{JSON.stringify(sanitizeObject(row.metadata), null, 2)}</pre>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={emptyStateStyle}>暂无失败、部分成功或跳过的主动检测明细。</div>
              )}
            </div>
          )}
        </div>
      </section>
    </section>
  )
}

const selectStyle: React.CSSProperties = {
  minHeight: 34,
  border: '1px solid rgba(129,160,207,0.18)',
  borderRadius: 'var(--radius-sm)',
  background: 'rgba(10,18,32,0.78)',
  color: 'var(--color-text-primary)',
  padding: '0 10px',
}

const tdPad: React.CSSProperties = {
  padding: '10px 12px',
  borderBottom: '1px solid rgba(129,160,207,0.12)',
  textAlign: 'left',
  verticalAlign: 'top',
}

const emptyStateStyle: React.CSSProperties = {
  padding: 28,
  border: '1px dashed rgba(129,160,207,0.18)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--color-text-secondary)',
  textAlign: 'center',
}

const preStyle: React.CSSProperties = {
  maxHeight: 280,
  overflow: 'auto',
  margin: '8px 0',
  padding: 12,
  border: '1px solid rgba(129,160,207,0.12)',
  borderRadius: 'var(--radius-sm)',
  background: 'rgba(2,6,23,0.5)',
  color: 'var(--color-text-secondary)',
  whiteSpace: 'pre-wrap',
}
