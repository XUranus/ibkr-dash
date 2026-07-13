import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface EvalRunCompareDialogProps {
  [key: string]: unknown
}

export default function EvalRunCompareDialog(props: EvalRunCompareDialogProps) {
  return (
    <div className="card">
      <div className="card__header">EvalRunCompareDialog</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
