import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchAccountOverview } from '@/api/account'
import type { AccountOverview } from '@/types/account'

let cachedOverview: AccountOverview | null = null
let pendingRequest: Promise<AccountOverview | null> | null = null
const listeners = new Set<() => void>()

function emitChange(): void {
  listeners.forEach((fn) => fn())
}

async function loadOverview(force = false): Promise<AccountOverview | null> {
  if (pendingRequest && !force) return pendingRequest
  if (cachedOverview && !force) return cachedOverview

  pendingRequest = (async () => {
    try {
      const response = await fetchAccountOverview()
      cachedOverview = response
      emitChange()
      return response
    } catch {
      return cachedOverview
    } finally {
      pendingRequest = null
    }
  })()

  return pendingRequest
}

export function useAccountOverview() {
  const [overview, setOverview] = useState(cachedOverview)

  useEffect(() => {
    const handler = () => setOverview(cachedOverview)
    listeners.add(handler)
    if (!cachedOverview) void loadOverview()
    return () => { listeners.delete(handler) }
  }, [])

  const refresh = useCallback(() => loadOverview(true), [])

  return { overview, ensureLoaded: loadOverview, refresh }
}
