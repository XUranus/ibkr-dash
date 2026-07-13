import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface RegressionProfilePanelProps {
  [key: string]: unknown
}

export default function RegressionProfilePanel(props: RegressionProfilePanelProps) {
  return (
    <div className="card">
      <div className="card__header">RegressionProfilePanel</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
