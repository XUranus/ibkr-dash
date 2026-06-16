export interface EmailSettings {
  smtp_host: string | null
  smtp_port: number | null
  smtp_username: string | null
  smtp_password_set: boolean
  encryption: 'SSL' | 'STARTTLS' | 'None'
  auth_method: 'password' | 'oauth2' | 'modern_auth'
  from_address: string | null
  to_addresses: string[]
  enabled: boolean
}

export interface EmailSettingsUpdate {
  smtp_host?: string | null
  smtp_port?: number | null
  smtp_username?: string | null
  smtp_password?: string | null
  encryption?: 'SSL' | 'STARTTLS' | 'None'
  auth_method?: 'password' | 'oauth2' | 'modern_auth'
  from_address?: string | null
  to_addresses?: string[] | null
  enabled?: boolean | null
}

export interface EmailTestResponse {
  success: boolean
  message: string
}
