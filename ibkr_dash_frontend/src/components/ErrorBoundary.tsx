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
        <div
          style={{
            display: 'grid',
            placeItems: 'center',
            minHeight: '40vh',
            padding: '2rem',
            textAlign: 'center',
            color: '#e2e8f0',
          }}
        >
          <div style={{ maxWidth: 480 }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>
              Something went wrong
            </h2>
            <p
              style={{
                color: '#94a3b8',
                fontSize: '0.95rem',
                lineHeight: 1.6,
                marginBottom: '1.5rem',
              }}
            >
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
