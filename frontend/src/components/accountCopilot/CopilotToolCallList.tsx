/** Copilot tool call list -- displays tool calls from a run. */

interface ToolCall {
  id: string
  tool_name: string
  arguments?: Record<string, unknown>
  result?: string
  status?: string
}

interface Props {
  toolCalls: ToolCall[]
  className?: string
}

export default function CopilotToolCallList({ toolCalls, className }: Props) {
  if (!toolCalls.length) return null

  return (
    <div className={`copilot-toolcalls ${className || ''}`}>
      <h4 className="copilot-toolcalls__title">Tool Calls</h4>
      <ul className="copilot-toolcalls__list">
        {toolCalls.map((tc) => (
          <li key={tc.id} className="copilot-toolcalls__item">
            <span className="copilot-toolcalls__name">{tc.tool_name}</span>
            {tc.status && (
              <span className={`copilot-toolcalls__status status-${tc.status === 'success' ? 'success' : 'secondary'}`}>
                {tc.status}
              </span>
            )}
            {tc.result && (
              <pre className="copilot-toolcalls__result">{tc.result}</pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
