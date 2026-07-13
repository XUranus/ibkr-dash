import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'

interface EvalCaseBulkEditDialogProps {
  [key: string]: unknown
}

export default function EvalCaseBulkEditDialog(props: EvalCaseBulkEditDialogProps) {
  return (
    <div className="card">
      <div className="card__header">EvalCaseBulkEditDialog</div>
      <div style={{ padding: 16, color: '#8b949e' }}>
        Component loading... (converting from Vue)
      </div>
    </div>
  )
}
