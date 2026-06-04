import { useState, useEffect, useCallback } from 'react'
import { fetchAuthSession, login, logout } from '@/api/auth'

const AUTH_CACHE_KEY = 'ibkr-dash.auth-session'
const AUTH_CACHE_TTL_MS = 30_000

interface AuthState {
  initialized: boolean
  loading: boolean
  authenticated: boolean
  username: string | null
}

function readCache(): { authenticated: boolean; username: string | null; cachedAt: number } | null {
  try {
    const raw = sessionStorage.getItem(AUTH_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (Date.now() - parsed.cachedAt > AUTH_CACHE_TTL_MS) {
      sessionStorage.removeItem(AUTH_CACHE_KEY)
      return null
    }
    return parsed
  } catch {
    sessionStorage.removeItem(AUTH_CACHE_KEY)
    return null
  }
}

function writeCache(authenticated: boolean, username: string | null): void {
  sessionStorage.setItem(AUTH_CACHE_KEY, JSON.stringify({ authenticated, username, cachedAt: Date.now() }))
}

let globalAuthState: AuthState = {
  initialized: false,
  loading: false,
  authenticated: false,
  username: null,
}

const listeners = new Set<() => void>()

function emitChange(): void {
  listeners.forEach((fn) => fn())
}

function applyState(authenticated: boolean, username: string | null): void {
  globalAuthState = {
    ...globalAuthState,
    authenticated,
    username: authenticated ? username : null,
    initialized: true,
  }
  writeCache(globalAuthState.authenticated, globalAuthState.username)
  emitChange()
}

export async function ensureAuthSession(force = false): Promise<void> {
  if (!force && globalAuthState.initialized) return

  if (!force) {
    const cached = readCache()
    if (cached) {
      applyState(cached.authenticated, cached.username)
      return
    }
  }

  globalAuthState = { ...globalAuthState, loading: true }
  emitChange()
  try {
    const session = await fetchAuthSession()
    applyState(session.authenticated, session.username)
  } catch {
    applyState(false, null)
  } finally {
    globalAuthState = { ...globalAuthState, loading: false }
    emitChange()
  }
}

export async function loginWithCredentials(username: string, password: string): Promise<void> {
  globalAuthState = { ...globalAuthState, loading: true }
  emitChange()
  try {
    const session = await login({ username, password })
    applyState(session.authenticated, session.username)
  } finally {
    globalAuthState = { ...globalAuthState, loading: false }
    emitChange()
  }
}

export async function logoutCurrentSession(): Promise<void> {
  globalAuthState = { ...globalAuthState, loading: true }
  emitChange()
  try {
    await logout()
    applyState(false, null)
  } finally {
    globalAuthState = { ...globalAuthState, loading: false }
    emitChange()
  }
}

export function useAuth(): AuthState & {
  ensureAuth: (force?: boolean) => Promise<void>
  loginWithCredentials: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
} {
  const [state, setState] = useState(globalAuthState)

  useEffect(() => {
    const handler = () => setState(globalAuthState)
    listeners.add(handler)
    return () => { listeners.delete(handler) }
  }, [])

  return {
    ...state,
    ensureAuth: ensureAuthSession,
    loginWithCredentials,
    logout: logoutCurrentSession,
  }
}
