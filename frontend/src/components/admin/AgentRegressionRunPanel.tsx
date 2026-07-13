import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface AgentRegressionRunPanelProps {
  [key: string]: unknown
}

export default function AgentRegressionRunPanel(props: AgentRegressionRunPanelProps) {
  return (
    <div className="card">
      <div className="card__header">AgentRegressionRunPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
