export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  authenticated: boolean
  username: string | null
}

export interface AuthSession {
  authenticated: boolean
  username: string | null
}
