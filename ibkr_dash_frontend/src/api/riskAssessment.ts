import { request } from './http'
import type { RiskAssessmentHealth, RiskAssessmentListResponse, RiskAssessmentResult } from '@/types/riskAssessment'

function toQueryString(params: Record<string, string | number | undefined | null>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const queryStr = searchParams.toString()
  return queryStr ? `?${queryStr}` : ''
}

export function fetchRiskAssessmentHealth(): Promise<RiskAssessmentHealth> {
  return request<RiskAssessmentHealth>('/api/risk-assessment/health')
}

export async function fetchRecentRiskAssessments(limit = 20): Promise<RiskAssessmentResult[]> {
  const response = await request<RiskAssessmentListResponse>(
    `/api/risk-assessment/assessments${toQueryString({ limit })}`,
  )
  return response.items ?? []
}

export function fetchRiskAssessmentDetail(id: string): Promise<RiskAssessmentResult> {
  return request<RiskAssessmentResult>(`/api/risk-assessment/assessments/${encodeURIComponent(id)}`)
}

export function triggerRiskAssessment(question?: string): Promise<RiskAssessmentResult> {
  return request<RiskAssessmentResult>('/api/risk-assessment/assess', {
    method: 'POST',
    body: JSON.stringify({ question: question || null }),
  })
}
