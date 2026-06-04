import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAuth, ensureAuthSession } from '../useAuth'

// Mock the auth API module
vi.mock('@/api/auth', () => ({
  fetchAuthSession: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}))

import { fetchAuthSession, login, logout } from '@/api/auth'

const mockedFetchAuthSession = vi.mocked(fetchAuthSession)
const mockedLogin = vi.mocked(login)
const mockedLogout = vi.mocked(logout)

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    // Reset global auth state by re-importing
  })

  it('returns initial auth state', () => {
    mockedFetchAuthSession.mockResolvedValueOnce({
      authenticated: false,
      username: null,
    })

    const { result } = renderHook(() => useAuth())

    // Should have the state fields
    expect(result.current).toHaveProperty('authenticated')
    expect(result.current).toHaveProperty('username')
    expect(result.current).toHaveProperty('loading')
    expect(result.current).toHaveProperty('initialized')
    expect(result.current).toHaveProperty('ensureAuth')
    expect(result.current).toHaveProperty('loginWithCredentials')
    expect(result.current).toHaveProperty('logout')
  })

  it('provides ensureAuth function', () => {
    mockedFetchAuthSession.mockResolvedValueOnce({
      authenticated: false,
      username: null,
    })

    const { result } = renderHook(() => useAuth())
    expect(typeof result.current.ensureAuth).toBe('function')
  })

  it('provides loginWithCredentials function', () => {
    mockedFetchAuthSession.mockResolvedValueOnce({
      authenticated: false,
      username: null,
    })

    const { result } = renderHook(() => useAuth())
    expect(typeof result.current.loginWithCredentials).toBe('function')
  })

  it('provides logout function', () => {
    mockedFetchAuthSession.mockResolvedValueOnce({
      authenticated: false,
      username: null,
    })

    const { result } = renderHook(() => useAuth())
    expect(typeof result.current.logout).toBe('function')
  })

  it('loginWithCredentials calls the login API', async () => {
    mockedFetchAuthSession.mockResolvedValue({
      authenticated: false,
      username: null,
    })
    mockedLogin.mockResolvedValueOnce({
      authenticated: true,
      username: 'testuser',
    })

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.loginWithCredentials('testuser', 'password123')
    })

    expect(mockedLogin).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123',
    })
  })

  it('logout calls the logout API', async () => {
    mockedFetchAuthSession.mockResolvedValue({
      authenticated: false,
      username: null,
    })
    mockedLogout.mockResolvedValueOnce({
      authenticated: false,
      username: null,
    })

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.logout()
    })

    expect(mockedLogout).toHaveBeenCalled()
  })
})
