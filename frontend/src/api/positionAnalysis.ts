import { request } from './http'

export interface PositionAnalysisResult {
  id: string
  report_date: string
  lang: string
  report: string
  created_at: string
}

export function fetchLatestPositionAnalysis(lang: string = 'zh'): Promise<PositionAnalysisResult> {
  return request<PositionAnalysisResult>(`/api/position-analysis/latest?lang=${lang}`)
}

export function triggerPositionAnalysis(): Promise<PositionAnalysisResult> {
  return request<PositionAnalysisResult>('/api/position-analysis/generate', { method: 'POST' })
}
