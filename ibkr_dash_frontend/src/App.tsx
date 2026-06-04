import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import AppHeader from '@/components/AppHeader'
import ErrorBoundary from '@/components/ErrorBoundary'
import { ensureAuthSession } from '@/hooks/useAuth'

export default function App() {
  useEffect(() => {
    void ensureAuthSession()
  }, [])

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="app-content">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  )
}
