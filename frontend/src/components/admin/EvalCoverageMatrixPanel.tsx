import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface EvalCoverageMatrixPanelProps {
  [key: string]: unknown
}

export default function EvalCoverageMatrixPanel(props: EvalCoverageMatrixPanelProps) {
  return (
    <div className="card">
      <div className="card__header">EvalCoverageMatrixPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
