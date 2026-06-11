import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import i18n from '@/i18n'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'
import type { EChartsType } from 'echarts/core'
import type { GraphSeriesOption } from 'echarts'
import { applyGraphEvent, buildAgentTaskEventsUrl, fetchAgentTaskGraph } from '@/api/agentTasks'
import type { AgentGraphNode, AgentGraphNodeStatus, AgentGraphSnapshot, AgentTask } from '@/types/agentTasks'

echarts.use([GraphChart, CanvasRenderer, TooltipComponent])

interface AgentTaskGraphProps {
  task: AgentTask
  expanded: boolean
  onSnapshot?: (taskId: string, snapshot: AgentGraphSnapshot | null) => void
}

export default function AgentTaskGraph({ task, expanded, onSnapshot }: AgentTaskGraphProps) {
  const chartElRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<EChartsType | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const pollTimerRef = useRef<number | undefined>(undefined)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)

  const [snapshot, setSnapshot] = useState<AgentGraphSnapshot | null>(task.graph_snapshot)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'live' | 'polling' | 'done' | 'error'>('idle')

  const selectedNode = useMemo(() => {
    if (!snapshot) return null
    return snapshot.nodes.find((n) => n.id === selectedNodeId)
      ?? snapshot.nodes.find((n) => n.status === 'running')
      ?? snapshot.nodes[0]
      ?? null
  }, [snapshot, selectedNodeId])

  const selectedNodeToolSteps = useMemo(() => {
    if (!selectedNode) return []
    if (selectedNode.tool_calls?.length) return selectedNode.tool_calls
    return (selectedNode.tools_called || []).map((name) => ({ tool_name: name, success: null, empty_result: null, error_type: null }))
  }, [selectedNode])

  const progressLabel = useMemo(() => {
    const nodes = snapshot?.nodes || []
    const done = nodes.filter((n) => ['success', 'failed', 'fallback', 'skipped'].includes(n.status)).length
    return nodes.length ? `${done}/${nodes.length}` : '--'
  }, [snapshot])

  function statusColor(status: AgentGraphNodeStatus): string {
    if (status === 'running') return '#38bdf8'
    if (status === 'success') return '#34d399'
    if (status === 'failed') return '#fb7185'
    if (status === 'fallback') return '#f59e0b'
    if (status === 'skipped') return '#64748b'
    return '#334155'
  }

  function statusLabel(status: string): string {
    const key = `agentTask.${status}` as string
    const translated = i18n.t(key)
    return translated !== key ? translated : status
  }

  function closeLiveUpdates(): void {
    sourceRef.current?.close()
    sourceRef.current = null
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = undefined
    }
  }

  function renderChart(currentSnapshot: AgentGraphSnapshot, currentChart: EChartsType, currentSelectedNodeId: string | null): void {
    if (!currentSnapshot) return
    const incoming = new Map<string, number>()
    currentSnapshot.nodes.forEach((node) => incoming.set(node.id, 0))
    currentSnapshot.edges.forEach((edge) => incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1))
    const levels = new Map<string, number>()
    const queue = currentSnapshot.nodes.filter((node) => (incoming.get(node.id) || 0) === 0).map((node) => node.id)
    queue.forEach((id) => levels.set(id, 0))
    const bfsQueue = [...queue]
    while (bfsQueue.length) {
      const id = bfsQueue.shift()!
      const level = levels.get(id) || 0
      currentSnapshot.edges.filter((edge) => edge.source === id).forEach((edge) => {
        const nextLevel = Math.max(levels.get(edge.target) || 0, level + 1)
        levels.set(edge.target, nextLevel)
        bfsQueue.push(edge.target)
      })
    }
    const grouped = new Map<number, AgentGraphNode[]>()
    currentSnapshot.nodes.forEach((node) => {
      const level = levels.get(node.id) || 0
      grouped.set(level, [...(grouped.get(level) || []), node])
    })
    const nodes = currentSnapshot.nodes.map((node) => {
      const level = levels.get(node.id) || 0
      const peers = grouped.get(level) || [node]
      const index = peers.findIndex((item) => item.id === node.id)
      return {
        name: node.id,
        id: node.id,
        nodeLabel: node.label,
        status: node.status,
        started_at: node.started_at,
        finished_at: node.finished_at,
        elapsed_ms: node.elapsed_ms,
        fallback_used: node.fallback_used,
        fallback_reason: node.fallback_reason,
        error: node.error,
        rounds_used: node.rounds_used,
        tools_called: node.tools_called,
        tool_calls: node.tool_calls,
        tool_call_count: node.tool_call_count,
        data_limitations_count: node.data_limitations_count,
        x: 80 + level * 150,
        y: 60 + index * 86 + Math.max(0, 2 - peers.length) * 32,
        itemStyle: { color: statusColor(node.status), borderColor: node.id === currentSelectedNodeId ? '#facc15' : 'rgba(255,255,255,0.18)', borderWidth: node.id === currentSelectedNodeId ? 3 : 1 },
      }
    })
    const series: GraphSeriesOption = {
      type: 'graph',
      layout: 'none',
      roam: false,
      symbolSize: 46,
      label: { show: true, color: '#dbeafe', fontSize: 11, formatter: (params) => String((params.data as { nodeLabel?: string }).nodeLabel || params.name) },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: 8,
      lineStyle: { color: 'rgba(148, 163, 184, 0.5)', width: 1.5, curveness: 0.06 },
      data: nodes,
      links: currentSnapshot.edges.map((edge) => ({ source: edge.source, target: edge.target })),
      animation: false,
    }
    currentChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (params: { dataType?: string; data?: unknown }) => {
          if (params.dataType !== 'node') return ''
          const data = params.data as AgentGraphNode & { nodeLabel?: string }
          return `${data.nodeLabel || data.id}<br/>${i18n.t('agentTask.status')}: ${statusLabel(data.status)}<br/>${i18n.t('agentTask.time')}: ${data.elapsed_ms || 0}ms<br/>${i18n.t('agentTask.tools')}: ${data.tool_call_count || 0}`
        },
      },
      series: [series],
    }, { notMerge: false, lazyUpdate: true })
  }

  useEffect(() => {
    if (!expanded) {
      closeLiveUpdates()
      return
    }

    let cancelled = false

    async function openGraph(): Promise<void> {
      const response = await fetchAgentTaskGraph(task.id)
      if (cancelled) return
      setSnapshot(response.graph_snapshot)
      onSnapshot?.(task.id, response.graph_snapshot)

      // Ensure chart instance
      if (chartElRef.current && !chartRef.current) {
        const instance = echarts.init(chartElRef.current, undefined, { renderer: 'canvas' })
        chartRef.current = instance
        resizeObserverRef.current = new ResizeObserver(() => chartRef.current?.resize())
        resizeObserverRef.current.observe(chartElRef.current)
        instance.on('click', (params) => {
          if (params.dataType === 'node' && typeof params.name === 'string') {
            setSelectedNodeId(params.name)
          }
        })
      }

      if (chartRef.current && response.graph_snapshot) {
        renderChart(response.graph_snapshot, chartRef.current, null)
      }

      if (task.status === 'completed' || task.status === 'failed') {
        setConnectionStatus('done')
        return
      }

      // Start SSE
      if (typeof EventSource !== 'undefined') {
        setConnectionStatus('live')
        const url = buildAgentTaskEventsUrl(task.id, response.graph_snapshot?.updated_seq || task.updated_seq || 0)
        const source = new EventSource(url, { withCredentials: true })
        sourceRef.current = source
        source.addEventListener('graph_event', (event) => {
          const parsed = JSON.parse((event as MessageEvent).data)
          setSnapshot((prev) => {
            const next = applyGraphEvent(prev, parsed)
            if (chartRef.current && next) renderChart(next, chartRef.current, null)
            onSnapshot?.(task.id, next)
            return next
          })
          if (parsed.type === 'graph_synced' || parsed.type === 'graph_failed') {
            setConnectionStatus(parsed.type === 'graph_failed' ? 'error' : 'done')
          }
        })
        source.onerror = () => {
          closeLiveUpdates()
          startPolling()
        }
      } else {
        startPolling()
      }
    }

    function startPolling(): void {
      setConnectionStatus('polling')
      pollTimerRef.current = window.setInterval(async () => {
        const response = await fetchAgentTaskGraph(task.id)
        setSnapshot(response.graph_snapshot)
        if (chartRef.current && response.graph_snapshot) renderChart(response.graph_snapshot, chartRef.current, null)
        onSnapshot?.(task.id, response.graph_snapshot)
        if (response.status === 'completed' || response.status === 'failed') {
          closeLiveUpdates()
          setConnectionStatus('done')
        }
      }, 1800)
    }

    void openGraph()

    return () => {
      cancelled = true
      closeLiveUpdates()
      resizeObserverRef.current?.disconnect()
      chartRef.current?.dispose()
      chartRef.current = null
    }
  }, [expanded, task.id, task.status, task.updated_seq, onSnapshot])

  return (
    <div style={{ marginTop: 12, border: '1px solid rgba(148, 163, 184, 0.18)', borderRadius: 8, background: 'rgba(15, 23, 42, 0.42)', padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, color: '#e2e8f0', fontWeight: 700 }}>
        <span>{i18n.t('agentTask.langGraphExecution')}</span>
        <small style={{ color: '#94a3b8', fontWeight: 500 }}>{progressLabel} {'·'} {connectionStatus}</small>
      </div>
      {snapshot ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 220px', gap: 12, minHeight: 320 }}>
          <div ref={chartElRef} style={{ minHeight: 320 }} />
          <aside style={{ borderLeft: '1px solid rgba(148, 163, 184, 0.16)', padding: '12px 0 12px 12px', color: '#cbd5e1', display: 'grid', gap: 8 }}>
            {selectedNode && (
              <>
                <strong>{selectedNode.label}</strong>
                <span style={{ fontSize: '0.8rem', color: selectedNode.status === 'success' ? '#34d399' : selectedNode.status === 'running' ? '#38bdf8' : selectedNode.status === 'failed' ? '#fb7185' : '#f59e0b' }}>
                  {statusLabel(selectedNode.status)}
                </span>
                <dl style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '8px 10px', margin: '12px 0' }}>
                  <dt style={{ color: '#94a3b8' }}>{i18n.t('agentTask.elapsed')}</dt>
                  <dd>{selectedNode.elapsed_ms || 0}ms</dd>
                  <dt style={{ color: '#94a3b8' }}>{i18n.t('agentTask.llmRounds')}</dt>
                  <dd>{selectedNode.rounds_used || 0}</dd>
                  <dt style={{ color: '#94a3b8' }}>{i18n.t('agentTask.tools')}</dt>
                  <dd>{selectedNode.tool_call_count || 0}</dd>
                  <dt style={{ color: '#94a3b8' }}>{i18n.t('agentTask.limitations')}</dt>
                  <dd>{selectedNode.data_limitations_count || 0}</dd>
                </dl>
                {selectedNodeToolSteps.length > 0 && (
                  <div style={{ display: 'grid', gap: 7, marginTop: 12 }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.78rem' }}>{i18n.t('agentTask.nodeExecution')}</span>
                    {selectedNodeToolSteps.map((tool, index) => (
                      <div key={`${tool.tool_name}-${index}`} style={{ display: 'grid', gridTemplateColumns: '8px minmax(0, 1fr) auto', gap: 8, alignItems: 'center', minHeight: 28, padding: '6px 8px', borderRadius: 6, background: 'rgba(15, 23, 42, 0.58)', color: '#dbeafe', fontSize: '0.8rem' }}>
                        <span style={{ width: 7, height: 7, borderRadius: 999, background: tool.success === false ? '#fb7185' : tool.empty_result ? '#f59e0b' : '#34d399' }} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tool.tool_name}</span>
                        <small style={{ color: '#94a3b8' }}>{tool.empty_result ? i18n.t('agentTask.empty') : tool.success === false ? (tool.error_type || i18n.t('agentTask.failed')) : i18n.t('agentTask.ok')}</small>
                      </div>
                    ))}
                  </div>
                )}
                {selectedNode.error && <p style={{ margin: '10px 0 0', overflowWrap: 'anywhere', fontSize: '0.82rem', color: '#fb7185' }}>{selectedNode.error}</p>}
                {selectedNode.fallback_reason && !selectedNode.error && <p style={{ margin: '10px 0 0', overflowWrap: 'anywhere', fontSize: '0.82rem', color: '#fbbf24' }}>{selectedNode.fallback_reason}</p>}
              </>
            )}
          </aside>
        </div>
      ) : (
        <div style={{ padding: '16px 0 4px', color: '#94a3b8' }}>{i18n.t('agentTask.noGraphSnapshot')}</div>
      )}
    </div>
  )
}
