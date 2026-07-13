export interface CopilotSession {
  id: string
  title: string
  status: 'active' | 'archived'
  created_at: string
  updated_at: string
  last_message_at: string | null
  message_count: number
  rolling_summary: string
  compressed_until_message_id: string | null
  pinned_facts: Record<string, unknown>
  metadata: Record<string, unknown>
}

export interface CopilotSessionListResponse {
  items: CopilotSession[]
}

export interface CopilotMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  run_id: string | null
  metadata: Record<string, unknown>
}

export interface CopilotMessageListResponse {
  items: CopilotMessage[]
}

export interface CopilotRun {
  id: string
  session_id: string
  user_message_id: string
  assistant_message_id: string | null
  status: 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'cancelled'
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
  user_input: string
  planner_output: Record<string, any>
  actions: Record<string, any>[]
  observations: Record<string, any>[]
  tool_calls: Record<string, any>[]
  skill_requests: Record<string, any>[]
  pending_approval: CopilotApproval | null
  memory_snapshot: Record<string, any>
  final_answer: string | null
  error_code: string | null
  error_message: string | null
  metadata: Record<string, any>
  _live_events?: CopilotEvent[]
  _live_final_answer?: string
  _streaming?: boolean
}

export interface CopilotSendMessageResponse {
  user_message: CopilotMessage
  assistant_message: CopilotMessage
  run: CopilotRun
}

export interface CopilotSendMessageStreamResponse {
  user_message: CopilotMessage
  run: CopilotRun
  events_url: string
}

export interface CopilotEvent {
  id: string
  run_id: string
  session_id: string
  event_type: string
  seq: number
  created_at: string
  payload: Record<string, any>
}

export interface CopilotApproval {
  approval_id: string
  run_id?: string
  session_id?: string
  skill_name: string
  skill_display_name?: string
  skill_arguments: Record<string, any>
  approval_message: string
  plan_hash: string
  status: 'pending' | 'awaiting_approval' | 'approved' | 'rejected' | 'expired' | 'executed' | 'failed'
  created_at?: string
  updated_at?: string
  expires_at?: string
  approved_at?: string | null
  rejected_at?: string | null
  executed_at?: string | null
  result_observation_id?: string | null
  data_access?: string[]
}

export interface CopilotApprovalRequest {
  approval_id: string
  approved: boolean
  plan_hash: string
  comment?: string
}

export interface CopilotApprovalResponse {
  run: CopilotRun
  assistant_message: CopilotMessage | null
}

export interface CopilotMemory {
  id: string
  session_id: string
  memory_type: string
  status: string
  created_at: string
  updated_at: string
  summary: string
  symbols: string[]
  topics: string[]
  user_intent: string
  important_facts: string[]
  user_preferences: string[]
  open_questions: string[]
  tool_facts: Record<string, any>[]
  skill_facts: Record<string, any>[]
}

export interface CopilotMemoryListResponse {
  items: CopilotMemory[]
}

export interface CopilotEventListResponse {
  items: CopilotEvent[]
}

export interface CopilotRunTraceResponse {
  run_id: string
  status: string
  timeline: CopilotTraceTimelineNode[]
  events: CopilotEvent[]
}

export interface CopilotTraceTimelineNode {
  node_type: string
  round?: number | null
  status: string
  label: string
  created_at: string
  payload: Record<string, any>
}

export interface CopilotHealthResponse {
  ok: boolean
  checks: Record<string, { ok: boolean; message?: string; count?: number }>
  settings: {
    max_react_rounds: number
    run_timeout_seconds: number
    max_event_payload_chars: number
    demo_mode: boolean
  }
}

export interface CopilotDemoSeedResponse {
  session: CopilotSession
  messages: CopilotMessage[]
  runs: CopilotRun[]
  memories: CopilotMemory[]
}

export interface AgentMonitoringRange {
  hours: number
  bucket: string
  source?: string
}

export interface AgentMonitoringStatusSummary {
  status: string
  success_rate_24h?: number
  failure_rate_24h?: number
  call_count_24h?: number
  p95_latency_ms_24h?: number
}

export interface AgentMonitoringOverviewResponse {
  range: AgentMonitoringRange
  ibkr: AgentMonitoringStatusSummary
  longbridge: AgentMonitoringStatusSummary
  llm: AgentMonitoringStatusSummary & { models: string[] }
  recent_failure_count: number
  last_probe_at: string
}

export interface AgentMetricSeriesItem {
  bucket_start: string
  success_rate: number
  failure_rate: number
  call_count: number
  avg_latency_ms: number
  p95_latency_ms: number
}

export interface AgentToolMetricsResponse {
  range: AgentMonitoringRange
  ibkr: { series: AgentMetricSeriesItem[] }
  longbridge: { series: AgentMetricSeriesItem[] }
}

export interface AgentMonitoringFailureItem {
  created_at: string
  kind: string
  name: string
  domain: string
  agent_name?: string
  error_message?: string | null
  latency_ms: number
  run_id: string
}

export interface AgentMonitoringFailureResponse {
  items: AgentMonitoringFailureItem[]
}

export interface AgentRecentToolCall {
  id: string
  tool_name: string
  tool_domain: string
  agent_name: string
  node_name: string
  ok: boolean
  latency_ms: number
  rolling_success_rate_10: number
  rolling_failure_rate_10: number
  rolling_window_size: number
  empty_result: boolean
  raw_ok: boolean
  compact_ok: boolean
  parsed_fields_count: number
  missing_fields_count: number
  error_code: string | null
  error_message: string | null
  run_id: string
  task_id: string
  created_at: string
}

export interface AgentRecentLlmCall {
  id: string
  agent_name: string
  node_name: string
  provider: string
  model: string
  call_type: string
  ok: boolean
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  rolling_success_rate_10: number
  rolling_window_size: number
  error_code: string | null
  error_message: string | null
  run_id: string
  task_id: string
  created_at: string
}

export interface AgentStructuredOutputEvent {
  id: string
  contract_name: string
  agent_name: string
  node_name: string
  ok: boolean
  repaired: boolean
  repair_attempts: number
  fallback_used: boolean
  schema_validation_passed: boolean
  rolling_success_rate_10: number
  rolling_repair_rate_10: number
  rolling_fallback_rate_10: number
  error_code: string | null
  error_message: string | null
  run_id: string
  task_id: string
  created_at: string
}

export interface CopilotToolProbeResult {
  id: string
  tool_name: string
  tool_domain: string
  status: string
  latency_ms: number
  error_code: string | null
  error_message: string | null
  created_at: string
  arguments_preview: Record<string, unknown> | null
  metadata: Record<string, unknown> | null
}

export interface CopilotToolReliabilityLatestResponse {
  results: CopilotToolProbeResult[]
}

export interface CopilotToolReliabilityProbeResponse {
  total: number
  pass: number
  fail: number
  skipped: number
  success_rate: number
  results: CopilotToolProbeResult[]
}
