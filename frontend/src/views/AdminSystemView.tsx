import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchSystemStatus } from '@/api/adminSystem'
import AdminTabs from '@/components/AdminTabs'
import type { AdminSystemStatus } from '@/types/adminSystem'

type StatusLevel = 'ok' | 'warning' | 'error'

const STATUS_COLOR: Record<StatusLevel, string> = {
  ok: 'var(--color-positive)',
  warning: '#ffb454',
  error: 'var(--color-negative)',
}

const STATUS_TAG: Record<StatusLevel, string> = {
  ok: 'tag--positive',
  warning: 'tag--warning',
  error: 'tag--negative',
}

function StatusIcon({ level }: { level: StatusLevel }) {
  const color = STATUS_COLOR[level]
  const size = 14
  if (level === 'ok') {
    return (
      <svg width={size} height={size} viewBox="0 0 14 14" fill="none" style={{ verticalAlign: 'middle' }}>
        <circle cx="7" cy="7" r="6" stroke={color} strokeWidth="1.5" />
        <path d="M4 7l2 2 4-4" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  if (level === 'warning') {
    return (
      <svg width={size} height={size} viewBox="0 0 14 14" fill="none" style={{ verticalAlign: 'middle' }}>
        <path d="M7 1L13 13H1L7 1z" stroke={color} strokeWidth="1.3" strokeLinejoin="round" />
        <line x1="7" y1="5.5" x2="7" y2="8.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="7" cy="10.5" r="0.8" fill={color} />
      </svg>
    )
  }
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" style={{ verticalAlign: 'middle' }}>
      <circle cx="7" cy="7" r="6" stroke={color} strokeWidth="1.5" />
      <path d="M4.5 4.5l5 5M9.5 4.5l-5 5" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

const rowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '6px 10px',
  borderRadius: 'var(--radius-sm)',
  background: 'rgba(10,14,26,0.4)',
  marginBottom: 6,
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={rowStyle}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-bright)', maxWidth: '60%', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>
    </div>
  )
}

function ServiceCard({
  name,
  level,
  statusLabel,
  details,
  delay,
}: {
  name: string
  level: StatusLevel
  statusLabel: string
  details: { label: string; value: React.ReactNode }[]
  delay: string
}) {
  return (
    <section className="surface-panel" style={{ animation: `slideUp 0.4s ease ${delay} both` }}>
      <div className="surface-panel__content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <StatusIcon level={level} /> {name}
          </h3>
          <span className={`tag ${STATUS_TAG[level]}`}>{statusLabel}</span>
        </div>
        <div style={{ display: 'grid', gap: 0 }}>
          {details.map((d) => (
            <DetailRow key={d.label} label={d.label} value={d.value} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default function AdminSystemView() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [status, setStatus] = useState<AdminSystemStatus | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      setStatus(await fetchSystemStatus())
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('adminSystem.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  const cards: { name: string; level: StatusLevel; statusLabel: string; details: { label: string; value: React.ReactNode }[] }[] = []

  if (status) {
    // Database
    cards.push({
      name: t('adminSystem.database'),
      level: status.database.healthy ? 'ok' : 'error',
      statusLabel: status.database.healthy ? t('adminSystem.healthy') : t('adminSystem.error'),
      details: [
        { label: t('adminSystem.path'), value: status.database.path },
        ...Object.entries(status.database.record_counts).map(([table, count]) => ({
          label: table,
          value: count.toLocaleString(),
        })),
      ],
    })

    // LLM
    cards.push({
      name: 'LLM',
      level: status.llm.configured ? 'ok' : 'warning',
      statusLabel: status.llm.configured ? t('adminSystem.configured') : t('adminSystem.notSet'),
      details: [
        { label: t('adminSystem.model'), value: status.llm.model },
        { label: t('adminSystem.baseUrl'), value: status.llm.base_url },
      ],
    })

    // IBKR
    cards.push({
      name: 'IBKR',
      level: status.ibkr.configured ? (status.ibkr.has_data ? 'ok' : 'warning') : 'error',
      statusLabel: status.ibkr.configured ? (status.ibkr.has_data ? t('adminSystem.configured') : t('adminSystem.noData')) : t('adminSystem.notSet'),
      details: [
        { label: t('adminSystem.configured'), value: status.ibkr.configured ? 'Yes' : 'No' },
        { label: t('adminSystem.hasData'), value: status.ibkr.has_data ? 'Yes' : 'No' },
        { label: t('adminSystem.latestDate'), value: status.ibkr.latest_date ?? '—' },
      ],
    })

    // Email
    cards.push({
      name: t('adminSystem.email'),
      level: status.email.configured ? (status.email.enabled ? 'ok' : 'warning') : 'error',
      statusLabel: status.email.configured ? (status.email.enabled ? t('adminSystem.enabled') : t('adminSystem.disabled')) : t('adminSystem.notSet'),
      details: [
        { label: t('adminSystem.configured'), value: status.email.configured ? 'Yes' : 'No' },
        { label: t('adminSystem.enabled'), value: status.email.enabled ? 'Yes' : 'No' },
      ],
    })

    // Longbridge
    const lb = status.longbridge
    const lbConnectivityLabel = lb.connectivity === 'ok' ? 'Connected' : lb.connectivity === 'error' ? 'Failed' : lb.connectivity === 'degraded' ? 'Degraded' : '—'
    cards.push({
      name: 'Longbridge',
      level: lb.configured ? (lb.connectivity === 'ok' ? 'ok' : lb.connectivity === 'error' ? 'error' : 'warning') : 'warning',
      statusLabel: lb.configured ? (lb.connectivity === 'ok' ? t('adminSystem.configured') : lbConnectivityLabel) : t('adminSystem.notSet'),
      details: [
        { label: 'App Key', value: lb.app_key_configured ? '✓' : '—' },
        { label: 'App Secret', value: lb.app_secret_configured ? '✓' : '—' },
        { label: 'Access Token', value: lb.access_token_configured ? '✓' : '—' },
        { label: 'SDK', value: lb.sdk_installed ? (lb.sdk_version ? `longport ${lb.sdk_version}` : 'longport ✓') : 'Not Installed' },
        { label: t('adminSystem.connectivity'), value: lbConnectivityLabel },
      ],
    })

    // Auth
    cards.push({
      name: t('adminSystem.auth'),
      level: status.auth.password_set ? 'ok' : 'warning',
      statusLabel: status.auth.password_set ? t('adminSystem.configured') : t('adminSystem.notSet'),
      details: [
        { label: t('adminSystem.passwordSet'), value: status.auth.password_set ? 'Yes' : 'No' },
      ],
    })

    // Scheduler
    cards.push({
      name: t('adminSystem.scheduler'),
      level: status.scheduler.enabled ? 'ok' : 'warning',
      statusLabel: status.scheduler.enabled ? t('adminSystem.enabled') : t('adminSystem.disabled'),
      details: [
        { label: t('adminSystem.enabled'), value: status.scheduler.enabled ? 'Yes' : 'No' },
      ],
    })

    // Runtime
    cards.push({
      name: t('adminSystem.runtime'),
      level: 'ok',
      statusLabel: status.runtime.app_env,
      details: [
        { label: t('adminSystem.python'), value: status.runtime.python_version.split(' ')[0] },
        { label: t('adminSystem.platform'), value: status.runtime.platform },
        { label: t('adminSystem.environment'), value: status.runtime.app_env },
        { label: t('adminSystem.timestamp'), value: new Date(status.timestamp).toLocaleString() },
      ],
    })
  }

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminSystem.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminSystem.title')}</h2>
            </div>
            {status && (
              <span className={`tag ${status.status === 'ok' ? 'tag--positive' : 'tag--negative'}`}>
                {status.status.toUpperCase()}
              </span>
            )}
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {status && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
          {cards.map((card, i) => (
            <ServiceCard
              key={card.name}
              name={card.name}
              level={card.level}
              statusLabel={card.statusLabel}
              details={card.details}
              delay={`${0.1 * (i + 1)}s`}
            />
          ))}
        </div>
      )}
    </section>
  )
}
