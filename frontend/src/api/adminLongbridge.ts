import { request } from './http'
import type { LongbridgeMcpTestResponse } from '@/types/adminLongbridgeMcp'

export function testLongbridgeConnection(): Promise<LongbridgeMcpTestResponse> {
  return request<LongbridgeMcpTestResponse>('/api/admin/longbridge/test-connection', {
    method: 'POST',
  })
}
