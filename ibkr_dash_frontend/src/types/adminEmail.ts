export interface EmailSettings {
  smtp_host: string | null
  smtp_port: number | null
  smtp_username: string | null
  smtp_password_set: boolean
  from_address: string | null
  to_addresses: string[]
  enabled: boolean
}

export interface EmailSettingsUpdate {
  smtp_host?: string | null
  smtp_port?: number | null
  smtp_username?: string | null
  smtp_password?: string | null
  from_address?: string | null
  to_addresses?: string[] | null
  enabled?: boolean | null
}

export interface EmailTestResponse {
  success: boolean
  message: string
}
