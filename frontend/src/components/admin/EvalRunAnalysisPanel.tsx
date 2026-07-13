import { useMemo } from 'react'
import type { EvalCaseResult, EvalRun } from '@/types/adminHarness'

interface EvalRunAnalysisPanelProps {
  run: EvalRun
}

function formatRate(value?: unknown): string {
  if (value === null || value === undefined || typeof value !== 'number' || Number.isNaN(value)) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function formatNumber(value?: unknown): string {
  if (value === null || value === undefined || typeof value !== 'number' || Number.isNaN(value)) return '-'
  return new Intl.NumberFormat().format(value)
}

function statusClass(status?: string | null): string {
  if (status === 'passed') return 'tag tag--positive'
  if (status === 'warning') return 'tag tag--warning'
  if (status === 'failed' || status === 'error') return 'tag tag--negative'
  return 'tag'
}

function severityClass(severity?: string | null): string {
  if (severity === 'critical') return 'tag tag--negative'
  if (severity === 'high') return 'tag tag--warning'
  if (severity === 'low') return 'tag tag--info'
  return 'tag'
}

function failedChecksForResult(result: EvalCaseResult): string[] {
  return (result.checks ?? [])
    .filter((c) => c.passed === false)
    .map((c) => c.check_name ?? 'unknown')
}

function resultMetadata(result: EvalCaseResult): Record<string, unknown> {
  return (result.metadata ?? {}) as Record<string, unknown>
}

function resultScope(result: EvalCaseResult): string {
  const meta = resultMetadata(result)
  return String(meta.eval_scope ?? 'agent')
}

function resultNodeName(result: EvalCaseResult): string {
  const meta = resultMetadata(result)
  const value = meta.node_name
  return value ? String(value) : '-'
}

export default function EvalRunAnalysisPanel({ run }: EvalRunAnalysisPanelProps) {
  const summary = run.summary ?? {}
  const results = run.results ?? []

  const statusCounts = (summary.status_counts as Record<string, number>) ?? {}
  const severityCounts = (summary.severity_counts as Record<string, number>) ?? {}
  const categoryCounts = (summary.category_counts as Record<string, number>) ?? {}
  const failedCheckCounts = (summary.failed_check_counts as Record<string, number>) ?? {}
  const failedCases = (summary.failed_cases as Array<Record<string, unknown>>) ?? []

  const topFailedChecks = useMemo(() => {
    return Object.entries(failedCheckCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
  }, [failedCheckCounts])

  const nodeSummary = useMemo(() => {
    let nodeCaseCount = 0
    const nodeNames: string[] = []
    for (const r of results) {
      if (resultScope(r) === 'node') {
        nodeCaseCount += 1
        const name = resultNodeName(r)
        if (name && name !== '-' && !nodeNames.includes(name)) {
          nodeNames.push(name)
        }
      }
    }
    return {
      node_case_count: nodeCaseCount,
      nodes: nodeNames,
      has_node_cases: nodeCaseCount > 0,
    }
  }, [results])

  return (
    <div className="eval-run-analysis">
      <section className="eval-run-analysis__section">
        <h4 className="eval-run-analysis__title">Overview</h4>
        <div className="eval-run-analysis__cards">
          <article className="eval-run-analysis__card">
            <span>Total Cases</span>
            <strong>{formatNumber(summary.case_count)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Pass Rate</span>
            <strong>{formatRate(summary.pass_rate)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Score Rate</span>
            <strong>{formatRate(summary.score_rate)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Passed</span>
            <strong className="color-positive">{formatNumber(summary.passed_count)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Warning</span>
            <strong className="color-warning">{formatNumber(summary.warning_count)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Failed</span>
            <strong className="color-negative">{formatNumber(summary.failed_count)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>Error</span>
            <strong className="color-negative">{formatNumber(summary.error_count)}</strong>
          </article>
          <article className="eval-run-analysis__card">
            <span>High/Critical Failures</span>
            <strong className="color-negative">{formatNumber(summary.high_priority_failure_count)}</strong>
          </article>
        </div>
      </section>

      {Object.keys(severityCounts).length > 0 && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">By Severity</h4>
          <div className="eval-run-analysis__tags">
            {Object.entries(severityCounts).map(([sev, count]) => (
              <span key={sev} className={severityClass(sev)}>{sev}: {count}</span>
            ))}
          </div>
        </section>
      )}

      {Object.keys(categoryCounts).length > 0 && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">By Category</h4>
          <div className="eval-run-analysis__tags">
            {Object.entries(categoryCounts).map(([cat, count]) => (
              <span key={cat} className="tag">{cat === 'uncategorized' ? 'Uncategorized' : cat}: {count}</span>
            ))}
          </div>
        </section>
      )}

      {topFailedChecks.length > 0 && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">Top Failed Checks</h4>
          <table className="eval-run-analysis__table">
            <thead><tr><th>Check</th><th>Failures</th></tr></thead>
            <tbody>
              {topFailedChecks.map(([name, count]) => (
                <tr key={name}>
                  <td><code>{name}</code></td>
                  <td>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {failedCases.length > 0 && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">Failed Cases</h4>
          <table className="eval-run-analysis__table">
            <thead><tr><th>case_id</th><th>status</th><th>severity</th><th>category</th><th>failed_checks</th><th>message</th></tr></thead>
            <tbody>
              {failedCases.map((fc, i) => (
                <tr key={String(fc.case_id) || i}>
                  <td><code>{String(fc.case_id)}</code></td>
                  <td><span className={statusClass(String(fc.status))}>{String(fc.status)}</span></td>
                  <td><span className={severityClass(String(fc.severity))}>{String(fc.severity)}</span></td>
                  <td>{String(fc.category || '-')}</td>
                  <td>{(fc.failed_checks as string[])?.join(', ') || '-'}</td>
                  <td>{String(fc.message || '-')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {nodeSummary.has_node_cases && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">Node Eval Summary</h4>
          <div className="eval-run-analysis__node-summary">
            <div><span>Node Cases</span><strong>{nodeSummary.node_case_count}</strong></div>
            <div><span>Nodes</span><strong>{nodeSummary.nodes.join(', ') || '-'}</strong></div>
          </div>
        </section>
      )}

      {results.length > 0 && (
        <section className="eval-run-analysis__section">
          <h4 className="eval-run-analysis__title">All Results</h4>
          <table className="eval-run-analysis__table">
            <thead>
              <tr>
                <th>case_id</th>
                <th>agent</th>
                <th>scope</th>
                <th>node_name</th>
                <th>status</th>
                <th>severity</th>
                <th>category</th>
                <th>score</th>
                <th>failed_checks</th>
                <th>error</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={String(r.case_id)}>
                  <td><code>{r.case_id}</code></td>
                  <td>{r.agent_name || '-'}</td>
                  <td>
                    {resultScope(r) === 'node'
                      ? <span className="tag tag--info">NODE</span>
                      : <span className="tag">AGENT</span>
                    }
                  </td>
                  <td>{resultNodeName(r)}</td>
                  <td><span className={statusClass(r.status ?? null)}>{r.status || '-'}</span></td>
                  <td><span className={severityClass(String(resultMetadata(r).severity || 'medium'))}>{String(resultMetadata(r).severity || 'medium')}</span></td>
                  <td>{String(resultMetadata(r).category || '-')}</td>
                  <td>{r.score ?? 0} / {r.max_score ?? 0}</td>
                  <td>{failedChecksForResult(r).join(', ') || '-'}</td>
                  <td>{r.error_code ? String(r.error_code) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <style>{`
        .eval-run-analysis {
          display: grid;
          gap: 1rem;
        }
        .eval-run-analysis__section {
          display: grid;
          gap: 8px;
        }
        .eval-run-analysis__title {
          margin: 0;
          font-size: 0.9rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .eval-run-analysis__cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
        }
        .eval-run-analysis__card {
          display: grid;
          gap: 4px;
          padding: 10px 12px;
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.5);
        }
        .eval-run-analysis__card span {
          font-size: 0.78rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .eval-run-analysis__card strong {
          font-size: 1.1rem;
        }
        .eval-run-analysis__tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .eval-run-analysis__table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.84rem;
        }
        .eval-run-analysis__table th,
        .eval-run-analysis__table td {
          padding: 8px;
          border-bottom: 1px solid rgba(129, 160, 207, 0.1);
          text-align: left;
        }
        .eval-run-analysis__table th {
          color: var(--color-text-secondary, #8ba0c0);
          font-weight: 700;
        }
        .eval-run-analysis__node-summary {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 8px;
        }
        .eval-run-analysis__node-summary > div {
          display: grid;
          gap: 4px;
          padding: 10px 12px;
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.5);
        }
        .eval-run-analysis__node-summary span {
          font-size: 0.78rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .color-positive { color: var(--color-positive, #58d6a1); }
        .color-warning { color: var(--color-warning, #f0b744); }
        .color-negative { color: var(--color-negative, #ff6b7a); }
      `}</style>
    </div>
  )
}
