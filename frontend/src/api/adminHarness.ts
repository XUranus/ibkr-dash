import { request } from './http'
import type {
  AgentReplaySnapshot,
  AgentReplaysListParams,
  AgentRegressionRunPayload,
  AgentRegressionRunResponse,
  AgentRunsListParams,
  AgentRunTraceDetail,
  AgentRunTraceListItem,
  EvalCase,
  EvalCasesListParams,
  EvalCoverageResponse,
  EvalRun,
  EvalRunPayload,
  EvalRunsListParams,
  HarnessListResponse,
  ImpactAnalysisResult,
  LLMCallMetric,
  LlmCallListParams,
  RegressionGateResult,
  RegressionProfile,
  RegressionProfileListResponse,
  RegressionProfileUpsertPayload,
} from '@/types/adminHarness'

function queryString(params: object): string {
  const search = new URLSearchParams()
  Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function listLlmCalls(params: LlmCallListParams = {}): Promise<HarnessListResponse<LLMCallMetric>> {
  return request<HarnessListResponse<LLMCallMetric>>(`/api/admin/llm-calls${queryString(params)}`)
}

export function listAgentRuns(params: AgentRunsListParams = {}): Promise<HarnessListResponse<AgentRunTraceListItem>> {
  return request<HarnessListResponse<AgentRunTraceListItem>>(`/api/admin/agent-runs${queryString(params)}`)
}

export function getAgentRun(runId: string): Promise<AgentRunTraceDetail> {
  return request<AgentRunTraceDetail>(`/api/admin/agent-runs/${encodeURIComponent(runId)}`)
}

export function listAgentReplays(params: AgentReplaysListParams = {}): Promise<HarnessListResponse<AgentReplaySnapshot>> {
  return request<HarnessListResponse<AgentReplaySnapshot>>(`/api/admin/agent-replays${queryString(params)}`)
}

export function getAgentReplay(replayId: string): Promise<AgentReplaySnapshot> {
  return request<AgentReplaySnapshot>(`/api/admin/agent-replays/${encodeURIComponent(replayId)}`)
}

export function getAgentReplayByRun(runId: string): Promise<AgentReplaySnapshot> {
  return request<AgentReplaySnapshot>(`/api/admin/agent-replays/by-run/${encodeURIComponent(runId)}`)
}

export function exportAgentReplay(replayId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/admin/agent-replays/${encodeURIComponent(replayId)}/export`)
}

export function listEvalCases(params: EvalCasesListParams = {}): Promise<HarnessListResponse<EvalCase>> {
  return request<HarnessListResponse<EvalCase>>(`/api/admin/agent-eval/cases${queryString(params)}`)
}

export function getEvalCase(caseId: string): Promise<EvalCase> {
  return request<EvalCase>(`/api/admin/agent-eval/cases/${encodeURIComponent(caseId)}`)
}

export function seedEvalCases(force = false): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/admin/agent-eval/cases/seed${queryString({ force })}`, {
    method: 'POST',
  })
}

export function createEvalCaseFromReplay(replayId: string, save = true): Promise<EvalCase> {
  return request<EvalCase>(`/api/admin/agent-eval/cases/from-replay/${encodeURIComponent(replayId)}${queryString({ save })}`, {
    method: 'POST',
  })
}

export function runEval(payload: EvalRunPayload): Promise<EvalRun> {
  return request<EvalRun>('/api/admin/agent-eval/runs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listEvalRuns(params: EvalRunsListParams = {}): Promise<HarnessListResponse<EvalRun>> {
  return request<HarnessListResponse<EvalRun>>(`/api/admin/agent-eval/runs${queryString(params)}`)
}

export function getEvalRun(evalRunId: string): Promise<EvalRun> {
  return request<EvalRun>(`/api/admin/agent-eval/runs/${encodeURIComponent(evalRunId)}`)
}

export function listRegressionProfiles(params: { limit?: number } = {}): Promise<RegressionProfileListResponse> {
  return request<RegressionProfileListResponse>(`/api/admin/agent-eval/regression-profiles${queryString(params)}`)
}

export function upsertRegressionProfile(agentName: string, payload: RegressionProfileUpsertPayload): Promise<RegressionProfile> {
  return request<RegressionProfile>(`/api/admin/agent-eval/regression-profiles/${encodeURIComponent(agentName)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function disableRegressionProfile(agentName: string): Promise<void> {
  return request<void>(`/api/admin/agent-eval/regression-profiles/${encodeURIComponent(agentName)}/disable`, {
    method: 'POST',
  })
}

export function buildRegressionPayloadFromProfile(agentName: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/admin/agent-eval/regression-profiles/${encodeURIComponent(agentName)}/build-payload`)
}

export function analyzeImpactChangedFiles(payload: { changed_files: string[]; base_ref?: string; head_ref?: string }): Promise<ImpactAnalysisResult> {
  return request<ImpactAnalysisResult>('/api/admin/agent-eval/impact/changed-files', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function analyzeImpactGitDiff(payload: { base_ref: string; head_ref: string }): Promise<ImpactAnalysisResult> {
  return request<ImpactAnalysisResult>('/api/admin/agent-eval/impact/git-diff', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function runAgentRegressionEval(payload: AgentRegressionRunPayload): Promise<AgentRegressionRunResponse> {
  return request<AgentRegressionRunResponse>('/api/admin/agent-eval/regression/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function regressionGateDryRun(payload: { changed_files?: string[]; base_ref?: string; head_ref?: string }): Promise<RegressionGateResult> {
  return request<RegressionGateResult>('/api/admin/agent-eval/regression/gate-dry-run', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getEvalCoverage(params: Record<string, unknown> = {}): Promise<EvalCoverageResponse> {
  return request<EvalCoverageResponse>(`/api/admin/agent-eval/coverage${queryString(params)}`)
}
