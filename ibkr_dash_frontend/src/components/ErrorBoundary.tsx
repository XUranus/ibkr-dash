import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, info.componentStack)
  }

  handleReload = (): void => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div style={{
          display: 'grid',
          placeItems: 'center',
          minHeight: '40vh',
          padding: '2rem',
          textAlign: 'center',
          animation: 'slideUp 0.4s ease',
        }}>
          <div style={{ maxWidth: 440 }}>
            {/* Amber accent line */}
            <div style={{
              width: 40,
              height: 2,
              background: 'var(--color-accent)',
              margin: '0 auto 1.5rem',
              borderRadius: 1,
            }} />
            <h2 style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '1.2rem',
              fontWeight: 600,
              marginBottom: '0.75rem',
              color: 'var(--color-text-bright)',
              letterSpacing: '-0.02em',
            }}>
              Something went wrong
            </h2>
            <p style={{
              color: 'var(--color-text-muted)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.82rem',
              lineHeight: 1.6,
              marginBottom: '1.5rem',
            }}>
              {this.state.error?.message || 'An unexpected error occurred while rendering this page.'}
            </p>
            <button
              className="btn btn--accent"
              onClick={this.handleReload}
              style={{ padding: '0.6rem 1.6rem' }}
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
