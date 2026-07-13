import { useEffect, useRef } from 'react'
import Modal from '@/components/Modal'

interface HarnessDetailDialogProps {
  visible: boolean
  header: string
  onClose: () => void
  children: React.ReactNode
}

export default function HarnessDetailDialog({ visible, header, onClose, children }: HarnessDetailDialogProps) {
  if (!visible) return null

  return (
    <Modal open={visible} onClose={onClose}>
      <div style={{ width: 'min(1340px, 92vw)', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div className="harness-detail-dialog__header">
          <span className="harness-detail-dialog__title">{header}</span>
          <button className="btn btn--secondary btn--sm" onClick={onClose}>✕</button>
        </div>
        <div className="harness-detail-dialog__body">
          {children}
        </div>
      </div>
    </Modal>
  )
}
