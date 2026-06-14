export interface ImportHistoryItem {
  id: number
  run_at: string
  file_path: string
  file_size: number
  status: string
  records_imported: Record<string, number> | null
  error: string | null
  started_at: string | null
  duration_ms: number | null
}

export interface ImportHistoryResponse {
  items: ImportHistoryItem[]
}

export interface TriggerAiReportResponse {
  success: boolean
  report_date: string
  created_at: string
  duration_ms: number
}

export interface TriggerImportResponse {
  success: boolean
  files: Record<string, Record<string, number>>
  errors: string[]
  started_at: string
  duration_ms: number
}
