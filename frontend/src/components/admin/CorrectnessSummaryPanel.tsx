import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface CorrectnessSummary {
  eval_run_count?: number
  judged_case_count?: number
  avg_overall_score?: number
  failed_dimension_count?: number
  high_risk_failure_count?: number
}

interface CorrectnessByAgent {
  agent_name: string
  judged_case_count?: number
  avg_overall_score?: number
  weakest_dimensions?: string[]
  failed_count?: number
}

interface CorrectnessByDimension {
  dimension: string
  avg_score?: number
  failed_count?: number
  warning_count?: number
  affected_agents?: string[]
}

interface CorrectnessRecentFailure {
  eval_run_id: string
  case_id: string
  agent_name?: string
  failed_dimensions?: string[]
  failure_reasons?: string[]
}

interface CorrectnessSummaryResponse {
  summary?: CorrectnessSummary
  by_agent?: CorrectnessByAgent[]
  by_dimension?: CorrectnessByDimension[]
  recent_failures?: CorrectnessRecentFailure[]
}

const SUMMARY_CARDS: { key: keyof CorrectnessSummary; label: string; format: 'int' | 'rate' | 'score' }[] = [
  { key: 'eval_run_count', label: 'Eval Runs', format: 'int' },
  { key: 'judged_case_count', label: 'Judged Cases', format: 'int' },
  { key: 'avg_overall_score', label: 'Avg Overall Score', format: 'score' },
  { key: 'failed_dimension_count', label: 'Failed Dimensions', format: 'int' },
  { key: 'high_risk_failure_count', label: 'High Risk Failures', format: 'int' },
]

function queryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return value.toFixed(2)
}

function formatCardValue(card: { format: 'int' | 'rate' | 'score' }, value: number | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  if (card.format === 'int') return String(value)
  if (card.format === 'score') return formatScore(value)
  if (card.format === 'rate') return `${(value * 100).toFixed(1)}%`
  return String(value)
}

function formatList(items: string[] | undefined | null): string {
  if (!items || !items.length) return '-'
  return items.join(', ')
}

export default function CorrectnessSummaryPanel() {
  const [summary, setSummary] = useState<CorrectnessSummary | null>(null)
  const [byAgent, setByAgent] = useState<CorrectnessByAgent[]>([])
  const [byDimension, setByDimension] = useState<CorrectnessByDimension[]>([])
  const [recentFailures, setRecentFailures] = useState<CorrectnessRecentFailure[]>([])
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const [filterAgentName, setFilterAgentName] = useState('')
  const [filterHours, setFilterHours] = useState(24 * 30)
  const [filterLimit, setFilterLimit] = useState(1000)

  const load = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const params: Record<string, unknown> = {
        hours: filterHours,
        limit: filterLimit,
      }
      if (filterAgentName.trim()) {
        params.agent_name = filterAgentName.trim()
      }
      const response: CorrectnessSummaryResponse = await request<CorrectnessSummaryResponse>(
        `/api/admin/eval/correctness-summary${queryString(params)}`
      )
      setSummary(response.summary ?? null)
      setByAgent(Array.isArray(response.by_agent) ? response.by_agent : [])
      setByDimension(Array.isArray(response.by_dimension) ? response.by_dimension : [])
      setRecentFailures(Array.isArray(response.recent_failures) ? response.recent_failures : [])
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load correctness report')
    } finally {
      setLoading(false)
    }
  }, [filterAgentName, filterHours, filterLimit])

  useEffect(() => {
    void load()
  }, [])

  return (
    <div className="correctness-panel">
      <div className="correctness-filters">
        <label>
          Agent
          <input value={filterAgentName} onChange={e => setFilterAgentName(e.target.value)} placeholder="All Agents" />
        </label>
        <label>
          Hours
          <input type="number" value={filterHours} onChange={e => setFilterHours(Number(e.target.value))} min={1} max={8760} />
        </label>
        <label>
          Limit
          <input type="number" value={filterLimit} onChange={e => setFilterLimit(Number(e.target.value))} min={1} max={5000} />
        </label>
        <button className="btn btn--primary" onClick={load} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {errorMessage && <p className="correctness-error">{errorMessage}</p>}

      <section className="correctness-section">
        <h4 className="correctness-section__title">Summary</h4>
        {summary ? (
          <div className="correctness-summary-grid">
            {SUMMARY_CARDS.map(card => (
              <article key={card.key} className="correctness-card">
                <span>{card.label}</span>
                <strong>{formatCardValue(card, summary[card.key])}</strong>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">No summary data</div>
        )}
      </section>

      <section className="correctness-section">
        <h4 className="correctness-section__title">By Agent</h4>
        <div className="table-shell">
          <table className="correctness-table">
            <thead>
              <tr>
                <th>agent_name</th>
                <th>judged_case_count</th>
                <th>avg_overall_score</th>
                <th>weakest_dimensions</th>
                <th>failed_count</th>
              </tr>
            </thead>
            <tbody>
              {byAgent.map(row => (
                <tr key={row.agent_name}>
                  <td><code>{row.agent_name}</code></td>
                  <td>{row.judged_case_count ?? '-'}</td>
                  <td>{formatScore(row.avg_overall_score)}</td>
                  <td>{formatList(row.weakest_dimensions)}</td>
                  <td>{row.failed_count ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {byAgent.length === 0 && <div className="empty-state">No agent data</div>}
      </section>

      <section className="correctness-section">
        <h4 className="correctness-section__title">By Dimension</h4>
        <div className="table-shell">
          <table className="correctness-table">
            <thead>
              <tr>
                <th>dimension</th>
                <th>avg_score</th>
                <th>failed_count</th>
                <th>warning_count</th>
                <th>affected_agents</th>
              </tr>
            </thead>
            <tbody>
              {byDimension.map(row => (
                <tr key={row.dimension}>
                  <td><code>{row.dimension}</code></td>
                  <td>{formatScore(row.avg_score)}</td>
                  <td>{row.failed_count ?? '-'}</td>
                  <td>{row.warning_count ?? '-'}</td>
                  <td>{formatList(row.affected_agents)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {byDimension.length === 0 && <div className="empty-state">No dimension data</div>}
      </section>

      <section className="correctness-section">
        <h4 className="correctness-section__title">Recent Failures</h4>
        <div className="table-shell">
          <table className="correctness-table">
            <thead>
              <tr>
                <th>eval_run_id</th>
                <th>case_id</th>
                <th>agent_name</th>
                <th>failed_dimensions</th>
                <th>failure_reasons</th>
              </tr>
            </thead>
            <tbody>
              {recentFailures.map(row => (
                <tr key={`${row.eval_run_id}-${row.case_id}`}>
                  <td><code>{row.eval_run_id || '-'}</code></td>
                  <td><code>{row.case_id || '-'}</code></td>
                  <td>{row.agent_name || '-'}</td>
                  <td>{formatList(row.failed_dimensions)}</td>
                  <td>{formatList(row.failure_reasons)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {recentFailures.length === 0 && <div className="empty-state">No recent failures</div>}
      </section>

      <style>{`
        .correctness-panel {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .correctness-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          align-items: flex-end;
        }
        .correctness-filters label {
          display: flex;
          flex-direction: column;
          font-size: 0.85rem;
          color: var(--color-text-secondary, #8ba0c0);
          gap: 0.25rem;
        }
        .correctness-filters input[type='text'],
        .correctness-filters input[type='number'],
        .correctness-filters input:not([type]) {
          min-width: 160px;
          padding: 0.4rem 0.6rem;
          border: 1px solid rgba(129, 160, 207, 0.18);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.72);
          color: var(--color-text-primary, #e0e8f0);
          font-size: 0.85rem;
        }
        .correctness-error {
          background: rgba(255, 107, 122, 0.1);
          color: var(--color-negative, #ff6b7a);
          padding: 0.5rem 0.75rem;
          border-radius: 4px;
          font-size: 0.85rem;
        }
        .correctness-summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 0.75rem;
        }
        .correctness-card {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
          padding: 0.75rem 1rem;
          background: rgba(10, 18, 32, 0.5);
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 6px;
        }
        .correctness-card span {
          font-size: 0.8rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .correctness-card strong {
          font-size: 1.1rem;
          color: var(--color-text-primary, #e0e8f0);
        }
        .correctness-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .correctness-section__title {
          margin: 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--color-text-primary, #e0e8f0);
        }
        .correctness-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.85rem;
        }
        .correctness-table th,
        .correctness-table td {
          padding: 0.45rem 0.6rem;
          text-align: left;
          border-bottom: 1px solid rgba(129, 160, 207, 0.1);
        }
        .correctness-table th {
          color: var(--color-text-secondary, #8ba0c0);
          font-weight: 600;
        }
        .correctness-table code {
          font-family: 'SFMono-Regular', Menlo, Consolas, monospace;
          font-size: 0.8rem;
          color: var(--primary-color, #2563eb);
          background: rgba(37, 99, 235, 0.08);
          padding: 0.05rem 0.35rem;
          border-radius: 3px;
        }
        .table-shell {
          overflow-x: auto;
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.3);
        }
        .empty-state {
          text-align: center;
          color: var(--color-text-secondary, #8ba0c0);
          font-size: 0.85rem;
          padding: 0.75rem;
        }
      `}</style>
    </div>
  )
}
