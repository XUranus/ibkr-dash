import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface GateReportsPanelProps {
  [key: string]: unknown
}

export default function GateReportsPanel(props: GateReportsPanelProps) {
  return (
    <div className="card">
      <div className="card__header">GateReportsPanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
