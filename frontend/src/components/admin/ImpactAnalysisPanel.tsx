import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface ImpactAnalysisPanelProps {
  [key: string]: unknown
}

export default function ImpactAnalysisPanel(props: ImpactAnalysisPanelProps) {
  return (
    <div className="card">
      <div className="card__header">ImpactAnalysisPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
