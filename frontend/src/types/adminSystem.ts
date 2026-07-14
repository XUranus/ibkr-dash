export interface AdminSystemStatus {
  status: string
  timestamp: string
  database: {
    healthy: boolean
    path: string
    record_counts: Record<string, number>
  }
  llm: {
    configured: boolean
    model: string
    base_url: string
  }
  longbridge: {
    configured: boolean
    app_key_configured: boolean
    app_secret_configured: boolean
    access_token_configured: boolean
    sdk_installed: boolean
    sdk_version: string | null
    connectivity: 'ok' | 'degraded' | 'error' | 'unchecked'
  }
  ibkr: {
    configured: boolean
    has_data: boolean
    latest_date: string | null
  }
  notifyhub?: {
    configured: boolean
    enabled: boolean
    url: string | null
    topic: string
  }
  auth: {
    password_set: boolean
  }
  scheduler: {
    enabled: boolean
  }
  runtime: {
    python_version: string
    platform: string
    app_env: string
  }
}
