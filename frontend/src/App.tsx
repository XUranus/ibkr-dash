import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import AppHeader from '@/components/AppHeader'
import ErrorBoundary from '@/components/ErrorBoundary'
import { useAuth } from '@/hooks/useAuth'

export default function App() {
  const { t } = useTranslation()
  const { initialized, ensureAuth } = useAuth()

  useEffect(() => {
    void ensureAuth()
  }, [])

  return (
    <div className="app-shell" style={{
      minHeight: '100vh',
      background: `
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(212,168,67,0.04) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(30,60,100,0.08) 0%, transparent 50%),
        var(--color-bg)
      `,
    }}>
      <AppHeader />
      <main className="app-content">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <footer style={{
        marginTop: 'var(--space-7)',
        paddingTop: 'var(--space-5)',
        borderTop: '1px solid var(--color-border-subtle)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 'var(--space-3)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.68rem',
          color: 'var(--color-text-muted)',
          letterSpacing: '0.08em',
        }}>
          {t('app.version')}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.68rem',
          color: 'var(--color-text-muted)',
        }}>
          {t('app.techStack')}
        </span>
      </footer>
    </div>
  )
}
