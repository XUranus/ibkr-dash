export interface RiskAssessmentHealth {
  status: string
  agent_name: string
  llm_configured: boolean
  message: string | null
}

export interface RiskDimension {
  score: number
  max_score: number
  risk_level: string
  findings: string[]
}

export interface RiskAssessmentResult {
  id: string
  assessment_type: string
  risk_report: {
    overall_risk_score: number
    risk_level: string
    summary: string
    concentration_risk?: RiskDimension
    sector_exposure?: RiskDimension
    liquidity_risk?: { cash_pct: number; deployable_liquidity: number; risk_level: string; findings: string[] }
    stress_test?: RiskDimension
    key_risks: string[]
    recommendations: string[]
    watch_points: string[]
    data_limitations: string[]
    evidence_used: string[]
  }
  metadata: Record<string, unknown> | null
  run_trace: unknown[] | null
  created_at: string | null
}

export interface RiskAssessmentListResponse {
  items: RiskAssessmentResult[]
}
