/** Copilot run trace panel -- displays run execution details. */

import type { CopilotRun } from '../../types/accountCopilot'

interface Props {
  run: CopilotRun | null
  onClose?: () => void
}

export default function CopilotRunTracePanel({ run, onClose }: Props) {
  if (!run) return null

  return (
    <div className="copilot-trace-panel">
      <div className="copilot-trace-panel__header">
        <h3>Run Trace</h3>
        {onClose && (
          <button className="copilot-trace-panel__close" onClick={onClose}>
            Close
          </button>
        )}
      </div>
      <div className="copilot-trace-panel__body">
        <dl className="copilot-trace-panel__meta">
          <dt>Run ID</dt>
          <dd>{run.id}</dd>
          <dt>Status</dt>
          <dd>{run.status}</dd>
          <dt>Session</dt>
          <dd>{run.session_id}</dd>
          {run.started_at && (
            <>
              <dt>Started</dt>
              <dd>{new Date(run.started_at).toLocaleString()}</dd>
            </>
          )}
          {run.completed_at && (
            <>
              <dt>Completed</dt>
              <dd>{new Date(run.completed_at).toLocaleString()}</dd>
            </>
          )}
        </dl>
        {run.tool_calls && run.tool_calls.length > 0 && (
          <>
            <h4 style={{ marginTop: 12, marginBottom: 4 }}>Tool Calls</h4>
            <pre className="copilot-trace-panel__trace">
              {JSON.stringify(run.tool_calls, null, 2)}
            </pre>
          </>
        )}
        {run.observations && run.observations.length > 0 && (
          <>
            <h4 style={{ marginTop: 12, marginBottom: 4 }}>Observations</h4>
            <pre className="copilot-trace-panel__trace">
              {JSON.stringify(run.observations, null, 2)}
            </pre>
          </>
        )}
      </div>
    </div>
  )
}
