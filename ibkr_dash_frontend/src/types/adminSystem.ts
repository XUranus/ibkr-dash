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
  }
  ibkr: {
    configured: boolean
    has_data: boolean
    latest_date: string | null
  }
  email: {
    configured: boolean
    enabled: boolean
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
