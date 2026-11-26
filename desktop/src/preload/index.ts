import { contextBridge, ipcRenderer } from 'electron'

export interface BackendInfo {
  port: number
  token: string
}

export interface AppInfo {
  version: string
  platform: string
  packaged: boolean
  logPath: string | null
}

export interface AutostartState {
  supported: boolean
  enabled: boolean
  reason?: string
}

const api = {
  getBackendInfo: (): Promise<BackendInfo | null> => ipcRenderer.invoke('fgh:backend-info'),
  getAppInfo: (): Promise<AppInfo> => ipcRenderer.invoke('fgh:app-info'),
  getAutostart: (): Promise<AutostartState> => ipcRenderer.invoke('fgh:autostart-get'),
  setAutostart: (enabled: boolean): Promise<AutostartState> =>
    ipcRenderer.invoke('fgh:autostart-set', enabled),
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke('fgh:open-external', url),
  openDataDir: (): Promise<void> => ipcRenderer.invoke('fgh:open-data-dir'),
  settingsChanged: (): void => {
    ipcRenderer.send('fgh:settings-changed')
  },
  quit: (): void => {
    ipcRenderer.send('fgh:quit')
  },
  platform: process.platform,
}

contextBridge.exposeInMainWorld('fgh', api)
