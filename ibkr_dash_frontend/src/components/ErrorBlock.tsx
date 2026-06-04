interface Props {
  message: string
}

export default function ErrorBlock({ message }: Props) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px',
      padding: '14px 16px',
      borderRadius: '14px',
      border: '1px solid rgba(255, 107, 125, 0.22)',
      background: 'rgba(63, 19, 30, 0.4)',
      color: '#ffd4da',
    }}>
      <span style={{ color: 'var(--color-negative)', flexShrink: 0 }}>⚠</span>
      <span>{message}</span>
    </div>
  )
}
