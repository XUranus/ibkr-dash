export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function formatDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const message = 'msg' in item ? String(item.msg) : 'Invalid parameter'
          const location = Array.isArray((item as { loc?: unknown }).loc)
            ? (item as { loc: unknown[] }).loc.join('.')
            : ''
          return location ? `${location}: ${message}` : message
        }
        return String(item)
      })
      .join('; ')
  }
  if (typeof detail === 'string') return detail
  return 'Request failed'
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? undefined)
  const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData
  const isBlob = typeof Blob !== 'undefined' && init.body instanceof Blob
  if (init.body !== undefined && !isFormData && !isBlob && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    credentials: 'include',
    ...init,
    headers,
  })

  // Handle 401 Unauthorized — clear auth state and redirect to home
  if (response.status === 401) {
    localStorage.removeItem('ibkr-dash.auth-session')
    window.location.href = '/'
    throw new ApiError('Authentication required.', 401)
  }

  // Handle 204 No Content (e.g., DELETE endpoints)
  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      throw new ApiError('Request timed out. The backend may still be processing. Please wait and try again.', response.status)
    }
    const isHtml = typeof payload === 'string' && payload.trimStart().startsWith('<')
    if (isHtml) {
      throw new ApiError('Gateway error. Please try again later.', response.status)
    }
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? formatDetail(payload.detail)
        : typeof payload === 'string'
          ? payload
          : `Request failed with status ${response.status}`
    throw new ApiError(detail, response.status)
  }

  return payload as T
}
