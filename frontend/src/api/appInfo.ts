import { request } from './http'

export interface AppInfo {
  app_name: string
}

export function fetchAppInfo(): Promise<AppInfo> {
  return request<AppInfo>('/api/app-info')
}
