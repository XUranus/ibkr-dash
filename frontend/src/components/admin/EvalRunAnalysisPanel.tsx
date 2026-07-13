import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface EvalRunAnalysisPanelProps {
  [key: string]: unknown
}

export default function EvalRunAnalysisPanel(props: EvalRunAnalysisPanelProps) {
  return (
    <div className="card">
      <div className="card__header">EvalRunAnalysisPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
