import { useTranslation } from 'react-i18next'

interface Props {
  message: string
}

export default function ErrorBlock({ message }: Props) {
  const { t } = useTranslation()

  return (
    <div
      role="alert"
      aria-label={t('common.error')}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '16px 20px',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid rgba(242, 92, 92, 0.18)',
        background: 'rgba(242, 92, 92, 0.04)',
        color: 'var(--color-negative)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.85rem',
        animation: 'slideUp 0.3s ease',
      }}
    >
      <span style={{ flexShrink: 0, fontSize: '1rem', lineHeight: 1.4 }}>⚠</span>
      <span style={{ lineHeight: 1.5 }}>{message}</span>
    </div>
  )
}
