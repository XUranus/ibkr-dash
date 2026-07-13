import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'
import HarnessDetailDialog from './HarnessDetailDialog'
import JsonBlock from './JsonBlock'

interface RegressionGateReportSummary {
  impacted_agent_count?: number
  recommended_run_count?: number
  executed_run_count?: number
  failed_run_count?: number
}

interface RegressionGateReport {
  report_id: string
  status: string
  ok: boolean
  dry_run: boolean
  trigger: string
  created_at?: string
  created_by?: string
  base_ref?: string
  head_ref?: string
  summary?: RegressionGateReportSummary
  reasons: string[]
  impacted_agents: unknown
  runs: unknown
  impact_analysis: unknown
}

interface RegressionGateReportListResponse {
  items: RegressionGateReport[]
  summary: {
    report_count: number
    passed_count: number
    failed_count: number
    dry_run_count: number
    error_count: number
  }
}

function queryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

function formatDateTime(iso: string | undefined): string {
  if (!iso) return '-'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function statusClass(status: string): string {
  if (status === 'passed') return 'tag tag--positive'
  if (status === 'failed') return 'tag tag--negative'
  if (status === 'error') return 'tag tag--negative'
  if (status === 'dry_run') return 'tag'
  return 'tag'
}

export default function GateReportsPanel() {
  const [reports, setReports] = useState<RegressionGateReport[]>([])
  const [summary, setSummary] = useState<RegressionGateReportListResponse['summary']>({
    report_count: 0, passed_count: 0, failed_count: 0, dry_run_count: 0, error_count: 0,
  })
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const [filterStatus, setFilterStatus] = useState('')
  const [filterTrigger, setFilterTrigger] = useState('')
  const [filterOk, setFilterOk] = useState<'' | 'true' | 'false'>('')
  const [filterDryRun, setFilterDryRun] = useState<'' | 'true' | 'false'>('')
  const [filterAgentName, setFilterAgentName] = useState('')
  const [filterHours, setFilterHours] = useState(24 * 30)
  const [filterLimit, setFilterLimit] = useState(100)

  const [selectedReport, setSelectedReport] = useState<RegressionGateReport | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const loadReports = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const params: Record<string, unknown> = { hours: filterHours, limit: filterLimit }
      if (filterStatus) params.status = filterStatus
      if (filterTrigger) params.trigger = filterTrigger
      if (filterOk) params.ok = filterOk === 'true'
      if (filterDryRun) params.dry_run = filterDryRun === 'true'
      if (filterAgentName) params.agent_name = filterAgentName
      const data = await request<RegressionGateReportListResponse>(
        `/api/admin/eval/regression-gate-reports${queryString(params)}`
      )
      setReports(data.items)
      setSummary(data.summary)
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [filterStatus, filterTrigger, filterOk, filterDryRun, filterAgentName, filterHours, filterLimit])

  const openReport = useCallback(async (reportId: string) => {
    setDetailLoading(true)
    try {
      const report = await request<RegressionGateReport>(
        `/api/admin/eval/regression-gate-reports/${encodeURIComponent(reportId)}`
      )
      setSelectedReport(report)
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setDetailLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadReports()
  }, [])

  return (
    <div className="gate-reports-panel">
      <div className="gate-reports-panel__header">
        <div className="gate-reports-panel__summary">
          <span>Total: {summary.report_count}</span>
          <span>Passed: {summary.passed_count}</span>
          <span>Failed: {summary.failed_count}</span>
          <span>Dry Run: {summary.dry_run_count}</span>
        </div>
        <button className="btn btn--secondary btn--sm" onClick={loadReports} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <div className="gate-reports-panel__filters">
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="passed">passed</option>
          <option value="failed">failed</option>
          <option value="dry_run">dry_run</option>
          <option value="error">error</option>
        </select>
        <select value={filterTrigger} onChange={e => setFilterTrigger(e.target.value)}>
          <option value="">All Triggers</option>
          <option value="cli">cli</option>
          <option value="api_dry_run">api_dry_run</option>
        </select>
        <select value={filterOk} onChange={e => setFilterOk(e.target.value as '' | 'true' | 'false')}>
          <option value="">All OK</option>
          <option value="true">ok=true</option>
          <option value="false">ok=false</option>
        </select>
        <select value={filterDryRun} onChange={e => setFilterDryRun(e.target.value as '' | 'true' | 'false')}>
          <option value="">All</option>
          <option value="true">dry_run=true</option>
          <option value="false">dry_run=false</option>
        </select>
        <input value={filterAgentName} onChange={e => setFilterAgentName(e.target.value)} placeholder="agent_name" />
        <button className="btn btn--secondary btn--sm" onClick={loadReports}>Search</button>
      </div>

      {errorMessage && <p className="gate-reports-panel__error">{errorMessage}</p>}

      {loading && reports.length === 0 && <div className="gate-reports-panel__empty">Loading...</div>}
      {!loading && reports.length === 0 && <div className="gate-reports-panel__empty">No gate reports found.</div>}

      {reports.length > 0 && (
        <table className="harness-table gate-reports-panel__table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Status</th>
              <th>OK</th>
              <th>Dry Run</th>
              <th>Trigger</th>
              <th>Impacted</th>
              <th>Recommended</th>
              <th>Executed</th>
              <th>Failed</th>
              <th>Base</th>
              <th>Head</th>
              <th>Report ID</th>
            </tr>
          </thead>
          <tbody>
            {reports.map(report => (
              <tr key={report.report_id} onClick={() => openReport(report.report_id)} style={{ cursor: 'pointer' }}>
                <td>{formatDateTime(report.created_at)}</td>
                <td><span className={statusClass(report.status)}>{report.status}</span></td>
                <td><span className={report.ok ? 'tag tag--positive' : 'tag tag--negative'}>{report.ok ? 'Yes' : 'No'}</span></td>
                <td>{report.dry_run ? 'Yes' : 'No'}</td>
                <td>{report.trigger}</td>
                <td>{report.summary?.impacted_agent_count ?? '-'}</td>
                <td>{report.summary?.recommended_run_count ?? '-'}</td>
                <td>{report.summary?.executed_run_count ?? '-'}</td>
                <td>{report.summary?.failed_run_count ?? '-'}</td>
                <td>{report.base_ref || '-'}</td>
                <td>{report.head_ref || '-'}</td>
                <td><code>{report.report_id}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <HarnessDetailDialog
        visible={Boolean(selectedReport)}
        header="Gate Report Detail"
        onClose={() => setSelectedReport(null)}
      >
        {selectedReport && (
          <>
            <div className="gate-reports-panel__detail-header">
              <span className={statusClass(selectedReport.status)}>{selectedReport.status}</span>
              <span>Trigger: {selectedReport.trigger}</span>
              <span>Created: {formatDateTime(selectedReport.created_at)}</span>
              {selectedReport.created_by && <span>By: {selectedReport.created_by}</span>}
            </div>
            <JsonBlock title="summary" value={selectedReport.summary} />
            {selectedReport.reasons.length > 0 && (
              <div className="gate-reports-panel__reasons">
                <h4>Reasons</h4>
                {selectedReport.reasons.map((reason, i) => (
                  <div key={i}>- {reason}</div>
                ))}
              </div>
            )}
            <JsonBlock title="impacted_agents" value={selectedReport.impacted_agents} collapsed />
            <JsonBlock title="runs" value={selectedReport.runs} collapsed />
            <JsonBlock title="impact_analysis" value={selectedReport.impact_analysis} collapsed />
            <JsonBlock title="full report" value={selectedReport} collapsed />
          </>
        )}
      </HarnessDetailDialog>

      <style>{`
        .gate-reports-panel {
          display: grid;
          gap: 1rem;
        }
        .gate-reports-panel__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }
        .gate-reports-panel__summary {
          display: flex;
          gap: 1rem;
          font-size: 0.85rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .gate-reports-panel__filters {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          align-items: center;
        }
        .gate-reports-panel__filters select,
        .gate-reports-panel__filters input {
          padding: 0.35rem 0.5rem;
          border: 1px solid rgba(129, 160, 207, 0.18);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.72);
          color: var(--color-text-primary, #e0e8f0);
          font-size: 0.82rem;
        }
        .gate-reports-panel__error {
          margin: 0;
          padding: 8px 12px;
          border-radius: 4px;
          background: rgba(255, 107, 122, 0.12);
          color: var(--color-negative, #ff6b7a);
          font-size: 0.85rem;
        }
        .gate-reports-panel__empty {
          padding: 2rem;
          text-align: center;
          color: var(--color-text-secondary, #8ba0c0);
          font-size: 0.9rem;
        }
        .gate-reports-panel__table {
          font-size: 0.82rem;
        }
        .gate-reports-panel__detail-header {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          align-items: center;
          margin-bottom: 0.75rem;
          font-size: 0.85rem;
        }
        .gate-reports-panel__reasons {
          margin: 0.5rem 0;
          padding: 0.75rem;
          border: 1px solid rgba(255, 107, 122, 0.2);
          border-radius: 4px;
          background: rgba(255, 107, 122, 0.05);
          font-size: 0.82rem;
        }
        .gate-reports-panel__reasons h4 {
          margin: 0 0 0.3rem;
          font-size: 0.85rem;
        }
      `}</style>
    </div>
  )
}
