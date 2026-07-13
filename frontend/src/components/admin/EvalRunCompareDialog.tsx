import HarnessDetailDialog from './HarnessDetailDialog'

interface EvalRunCompareDialogProps {
  visible: boolean
  result: Record<string, unknown> | null
  loading?: boolean
  onClose: () => void
}

function formatRate(value?: unknown): string {
  if (value === null || value === undefined || typeof value !== 'number' || Number.isNaN(value)) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function formatDelta(value?: unknown): string {
  if (value === null || value === undefined || typeof value !== 'number' || Number.isNaN(value)) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

function deltaClass(value?: unknown): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return ''
  return value > 0 ? 'eval-run-compare__delta-positive' : value < 0 ? 'eval-run-compare__delta-negative' : ''
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

export default function EvalRunCompareDialog({ visible, result, loading, onClose }: EvalRunCompareDialogProps) {
  const summary = (result?.summary as Record<string, unknown>) ?? {}
  const newFailures = (result?.new_failures as Array<Record<string, unknown>>) ?? []
  const fixedCases = (result?.fixed_cases as Array<Record<string, unknown>>) ?? []
  const stillFailing = (result?.still_failing as Array<Record<string, unknown>>) ?? []
  const missingInCandidate = (result?.missing_in_candidate as Array<Record<string, unknown>>) ?? []
  const newCasesInCandidate = (result?.new_cases_in_candidate as Array<Record<string, unknown>>) ?? []

  return (
    <HarnessDetailDialog visible={visible} header="Eval Run Comparison" onClose={onClose}>
      {loading && <div className="empty-state">Loading...</div>}
      {!loading && !result && <div className="empty-state">No comparison data</div>}
      {!loading && result && (
        <div className="eval-run-compare">
          <section className="eval-run-compare__section">
            <h4 className="eval-run-compare__title">Overview</h4>
            <div className="eval-run-compare__cards">
              <article className="eval-run-compare__card">
                <span>Baseline Pass Rate</span>
                <strong>{formatRate(summary.baseline_pass_rate)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>Candidate Pass Rate</span>
                <strong>{formatRate(summary.candidate_pass_rate)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>Pass Rate Delta</span>
                <strong className={deltaClass(summary.pass_rate_delta)}>{formatDelta(summary.pass_rate_delta)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>Score Rate Delta</span>
                <strong className={deltaClass(summary.score_rate_delta)}>{formatDelta(summary.score_rate_delta)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>New Failures</span>
                <strong className="color-negative">{String(summary.new_failure_count ?? 0)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>Fixed</span>
                <strong className="color-positive">{String(summary.fixed_case_count ?? 0)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>High/Critical Regressions</span>
                <strong className="color-negative">{String(summary.high_priority_regression_count ?? 0)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>Missing in Candidate</span>
                <strong className="color-negative">{String(summary.missing_in_candidate_count ?? 0)}</strong>
              </article>
              <article className="eval-run-compare__card">
                <span>New in Candidate</span>
                <strong className="color-positive">{String(summary.new_case_in_candidate_count ?? 0)}</strong>
              </article>
            </div>
          </section>

          <section className="eval-run-compare__section">
            <h4 className="eval-run-compare__title">New Failures</h4>
            {newFailures.length > 0 ? (
              <table className="eval-run-compare__table">
                <thead><tr><th>case_id</th><th>severity</th><th>category</th><th>baseline</th><th>candidate</th><th>new_failed_checks</th><th>message</th></tr></thead>
                <tbody>
                  {newFailures.map((item, i) => (
                    <tr key={String(item.case_id) || i}>
                      <td><code>{String(item.case_id)}</code></td>
                      <td><span className={severityClass(String(item.severity))}>{String(item.severity)}</span></td>
                      <td>{String(item.category || '-')}</td>
                      <td><span className={statusClass(String(item.baseline_status))}>{String(item.baseline_status)}</span></td>
                      <td><span className={statusClass(String(item.candidate_status))}>{String(item.candidate_status)}</span></td>
                      <td>{(item.new_failed_checks as string[])?.join(', ') || '-'}</td>
                      <td>{String(item.message || '-')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">No new failures</div>
            )}
          </section>

          <section className="eval-run-compare__section">
            <h4 className="eval-run-compare__title">Fixed Cases</h4>
            {fixedCases.length > 0 ? (
              <table className="eval-run-compare__table">
                <thead><tr><th>case_id</th><th>severity</th><th>category</th><th>baseline</th><th>candidate</th><th>fixed_failed_checks</th></tr></thead>
                <tbody>
                  {fixedCases.map((item, i) => (
                    <tr key={String(item.case_id) || i}>
                      <td><code>{String(item.case_id)}</code></td>
                      <td><span className={severityClass(String(item.severity))}>{String(item.severity)}</span></td>
                      <td>{String(item.category || '-')}</td>
                      <td><span className={statusClass(String(item.baseline_status))}>{String(item.baseline_status)}</span></td>
                      <td><span className={statusClass(String(item.candidate_status))}>{String(item.candidate_status)}</span></td>
                      <td>{(item.fixed_failed_checks as string[])?.join(', ') || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">No fixed cases</div>
            )}
          </section>

          <section className="eval-run-compare__section">
            <h4 className="eval-run-compare__title">Still Failing</h4>
            {stillFailing.length > 0 ? (
              <table className="eval-run-compare__table">
                <thead><tr><th>case_id</th><th>severity</th><th>category</th><th>candidate_failed_checks</th><th>message</th></tr></thead>
                <tbody>
                  {stillFailing.map((item, i) => (
                    <tr key={String(item.case_id) || i}>
                      <td><code>{String(item.case_id)}</code></td>
                      <td><span className={severityClass(String(item.severity))}>{String(item.severity)}</span></td>
                      <td>{String(item.category || '-')}</td>
                      <td>{(item.candidate_failed_checks as string[])?.join(', ') || '-'}</td>
                      <td>{String(item.message || '-')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">No still-failing cases</div>
            )}
          </section>

          {missingInCandidate.length > 0 && (
            <section className="eval-run-compare__section">
              <h4 className="eval-run-compare__title">Missing in Candidate</h4>
              <table className="eval-run-compare__table">
                <thead><tr><th>case_id</th><th>severity</th><th>category</th><th>baseline_status</th><th>score</th></tr></thead>
                <tbody>
                  {missingInCandidate.map((item, i) => (
                    <tr key={String(item.case_id) || i}>
                      <td><code>{String(item.case_id)}</code></td>
                      <td><span className={severityClass(String(item.severity))}>{String(item.severity)}</span></td>
                      <td>{String(item.category || '-')}</td>
                      <td><span className={statusClass(String(item.baseline_status))}>{String(item.baseline_status)}</span></td>
                      <td>{String(item.baseline_score ?? 0)}/{String(item.baseline_max_score ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {newCasesInCandidate.length > 0 && (
            <section className="eval-run-compare__section">
              <h4 className="eval-run-compare__title">New in Candidate</h4>
              <table className="eval-run-compare__table">
                <thead><tr><th>case_id</th><th>severity</th><th>category</th><th>candidate_status</th><th>score</th></tr></thead>
                <tbody>
                  {newCasesInCandidate.map((item, i) => (
                    <tr key={String(item.case_id) || i}>
                      <td><code>{String(item.case_id)}</code></td>
                      <td><span className={severityClass(String(item.severity))}>{String(item.severity)}</span></td>
                      <td>{String(item.category || '-')}</td>
                      <td><span className={statusClass(String(item.candidate_status))}>{String(item.candidate_status)}</span></td>
                      <td>{String(item.candidate_score ?? 0)}/{String(item.candidate_max_score ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </div>
      )}

      <style>{`
        .eval-run-compare {
          display: grid;
          gap: 1rem;
        }
        .eval-run-compare__section {
          display: grid;
          gap: 8px;
        }
        .eval-run-compare__title {
          margin: 0;
          font-size: 0.9rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .eval-run-compare__cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 8px;
        }
        .eval-run-compare__card {
          display: grid;
          gap: 4px;
          padding: 10px 12px;
          border: 1px solid rgba(129, 160, 207, 0.14);
          border-radius: 4px;
          background: rgba(10, 18, 32, 0.5);
        }
        .eval-run-compare__card span {
          font-size: 0.78rem;
          color: var(--color-text-secondary, #8ba0c0);
        }
        .eval-run-compare__card strong {
          font-size: 1.1rem;
        }
        .eval-run-compare__delta-positive {
          color: var(--color-positive, #58d6a1);
        }
        .eval-run-compare__delta-negative {
          color: var(--color-negative, #ff6b7a);
        }
        .eval-run-compare__table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.84rem;
        }
        .eval-run-compare__table th,
        .eval-run-compare__table td {
          padding: 8px;
          border-bottom: 1px solid rgba(129, 160, 207, 0.1);
          text-align: left;
        }
        .eval-run-compare__table th {
          color: var(--color-text-secondary, #8ba0c0);
          font-weight: 700;
        }
        .color-positive { color: var(--color-positive, #58d6a1); }
        .color-negative { color: var(--color-negative, #ff6b7a); }
      `}</style>
    </HarnessDetailDialog>
  )
}
