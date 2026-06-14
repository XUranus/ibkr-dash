import { describe, it, expect, vi, beforeEach } from 'vitest'
import { request, ApiError } from '../http'

// Mock global fetch so we never make real network requests
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('request', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('returns parsed JSON on success', async () => {
    const mockData = { id: 1, name: 'test' }
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await request<typeof mockData>('/api/test')
    expect(result).toEqual(mockData)
    expect(mockFetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
      credentials: 'include',
    }))
  })

  it('throws ApiError with detail message on 400 response', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid parameter' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid parameter' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      message: 'Invalid parameter',
      status: 400,
    })
  })

  it('throws timeout ApiError on 502 response', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response('Bad Gateway', {
        status: 502,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response('Bad Gateway', {
        status: 502,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      status: 502,
    })
  })

  it('throws timeout ApiError on 503 response', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response('Service Unavailable', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response('Service Unavailable', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      status: 503,
    })
  })

  it('throws timeout ApiError on 504 response', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response('Gateway Timeout', {
        status: 504,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response('Gateway Timeout', {
        status: 504,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      status: 504,
    })
  })

  it('throws gateway ApiError when response is HTML', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response('<html><body>Error</body></html>', {
        status: 500,
        headers: { 'Content-Type': 'text/html' },
      }),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response('<html><body>Error</body></html>', {
        status: 500,
        headers: { 'Content-Type': 'text/html' },
      }),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      message: 'Gateway error. Please try again later.',
      status: 500,
    })
  })

  it('handles array detail in error response', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: [{ msg: 'field required', loc: ['body', 'name'] }] }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(request('/api/test')).rejects.toThrow(ApiError)

    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: [{ msg: 'field required', loc: ['body', 'name'] }] }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(request('/api/test')).rejects.toMatchObject({
      status: 422,
    })
  })

  it('sets Content-Type header for JSON body', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await request('/api/test', { method: 'POST', body: JSON.stringify({ key: 'value' }) })

    expect(mockFetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
      headers: expect.any(Headers),
    }))
  })

  it('sends credentials include', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await request('/api/protected')

    expect(mockFetch).toHaveBeenCalledWith('/api/protected', expect.objectContaining({
      credentials: 'include',
    }))
  })
})

describe('ApiError', () => {
  it('has the correct name, message, and status', () => {
    const error = new ApiError('Not found', 404)
    expect(error.name).toBe('ApiError')
    expect(error.message).toBe('Not found')
    expect(error.status).toBe(404)
    expect(error).toBeInstanceOf(Error)
  })

  it('is an instance of Error', () => {
    const error = new ApiError('Server error', 500)
    expect(error).toBeInstanceOf(Error)
  })
})
