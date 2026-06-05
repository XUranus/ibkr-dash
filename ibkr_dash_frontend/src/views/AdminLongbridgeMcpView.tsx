import { useTranslation } from 'react-i18next'
import AdminTabs from '@/components/AdminTabs'

export default function AdminLongbridgeMcpView() {
  const { t } = useTranslation()

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('adminLongbridge.adminLabel')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('adminLongbridge.title')}</h2>
              <p className="panel-subtitle">{t('adminLongbridge.subtitle')}</p>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('adminLongbridge.status')}</p>
          <div style={{ marginTop: 12 }}>
            <span className="tag tag--warning">{t('adminLongbridge.notConfigured')}</span>
            <p style={{ marginTop: 12, color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
              {t('adminLongbridge.notConfiguredDesc')}
            </p>
            <pre style={{ marginTop: 12, padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.6)', border: '1px solid var(--color-border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--color-text-secondary)', overflow: 'auto' }}>
{`LONGBRIDGE_APP_KEY=your-app-key
LONGBRIDGE_APP_SECRET=your-app-secret
LONGBRIDGE_ACCESS_TOKEN=your-access-token`}
            </pre>
          </div>
        </div>
      </section>
    </section>
  )
}
