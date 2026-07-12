/** Safe JSON utilities. */

/**
 * Parse JSON safely, returning a fallback on error.
 */
export function safeJsonParse<T>(value: string | T, fallback: T): T {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}
