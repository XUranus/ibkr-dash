export interface NotifyHubSettings {
  enabled: boolean
  url: string | null
  api_key_set: boolean
  topic: string
}

export interface NotifyHubSettingsUpdate {
  enabled?: boolean | null
  url?: string | null
  api_key?: string | null
  topic?: string | null
}

export interface NotifyHubTestResponse {
  success: boolean
  message: string
}
