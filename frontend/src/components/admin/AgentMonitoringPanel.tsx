import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface AgentMonitoringPanelProps {
  [key: string]: unknown
}

export default function AgentMonitoringPanel(props: AgentMonitoringPanelProps) {
  return (
    <div className="card">
      <div className="card__header">AgentMonitoringPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
