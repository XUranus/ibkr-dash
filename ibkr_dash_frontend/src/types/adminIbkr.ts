export interface IbkrSettings {
  flex_token: string | null
  flex_query_id: string | null
  flex_query_ids: string | null
  account_id: string | null
}

export interface IbkrSettingsUpdate {
  flex_token?: string | null
  flex_query_id?: string | null
  flex_query_ids?: string | null
  account_id?: string | null
}

export interface IbkrTestResponse {
  success: boolean
  message: string
  account_id: string | null
}
