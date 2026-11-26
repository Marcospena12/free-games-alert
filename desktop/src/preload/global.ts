import type { AppInfo, AutostartState, BackendInfo } from './index'

export interface FghApi {
  getBackendInfo(): Promise<BackendInfo | null>
  getAppInfo(): Promise<AppInfo>
  getAutostart(): Promise<AutostartState>
  setAutostart(enabled: boolean): Promise<AutostartState>
  openExternal(url: string): Promise<void>
  openDataDir(): Promise<void>
  settingsChanged(): void
  quit(): void
  platform: string
}

declare global {
  interface Window {
    fgh: FghApi
  }
}
