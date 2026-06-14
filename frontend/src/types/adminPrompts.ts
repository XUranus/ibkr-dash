export interface PromptItem {
  id: number
  prompt_key: string
  version: number
  content: string
  status: string
  created_at: string
}

export interface PromptCreatePayload {
  prompt_key: string
  content: string
  status?: string
}
