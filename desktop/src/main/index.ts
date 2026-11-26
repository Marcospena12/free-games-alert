import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  nativeImage,
  session,
  shell,
  Tray,
} from 'electron'
import { existsSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

import { BackendProcess, type BackendInfo } from './backend'
import { cleanupLegacyAutostart, getAutostart, setAutostart } from './autostart'
import { log } from './log'
import { loadWindowState, trackWindowState } from './window-state'

const APP_ID = 'br.com.marco.freegameshub'
const ASSET_TRAY = 'tray.png'
const ASSET_ICON = 'icon.png'

const gotLock = app.requestSingleInstanceLock()
const startHidden = process.argv.includes('--hidden')
const quitRequested = process.argv.includes('--quit')
const quitting = { value: false }

let mainWindow: BrowserWindow | null = null
let splashWindow: BrowserWindow | null = null
let splashShownAt = 0
let tray: Tray | null = null
let backend: BackendProcess | null = null
let trayNotifications = true
let trayAutostart = false
let rendererRecoveryOpen = false

if (process.platform === 'win32') {
  app.setAppUserModelId(APP_ID)
}

if (!gotLock) {
  // A instância primária recebe `second-instance` e decide o que fazer.
  app.quit()
} else {
  app.on('second-instance', (_event, argv) => {
    if (argv.includes('--quit')) {
      quitApp()
      return
    }
    // Uma segunda instância disparada pelo autostart não deve abrir a janela.
    if (argv.includes('--hidden')) return
    showMainWindow()
  })

  app.on('window-all-closed', () => {
    // A janela pode estar oculta na bandeja; só sai com `app.quit()`.
  })

  app.on('activate', () => showMainWindow())

  app.on('before-quit', () => {
    quitting.value = true
    backend?.stop()
  })

  app.on('will-quit', () => {
    backend?.stop()
    backend = null
    tray?.destroy()
    tray = null
  })

  process.on('uncaughtException', (err) => {
    log.error(`exceção não tratada: ${err.stack ?? err.message}`)
    showFatalError('Erro inesperado', err.message)
  })
  process.on('unhandledRejection', (reason) => {
    const message = reason instanceof Error ? reason.stack ?? reason.message : String(reason)
    log.error(`promise rejeitada: ${message}`)
  })

  if (quitRequested) {
    app.whenReady().then(() => app.quit()).catch(() => app.quit())
  } else {
    app.whenReady().then(onReady).catch((err) => {
      log.error(`falha na inicialização: ${String(err)}`)
      showFatalError('Não foi possível iniciar o Free Games Hub', String(err))
      app.quit()
    })
  }
}

async function onReady(): Promise<void> {
  log.info(`Free Games Hub iniciando (versão ${app.getVersion()}, empacotado=${app.isPackaged})`)
  cleanupLegacyAutostart()
  Menu.setApplicationMenu(null)
  configureSecurity()

  if (!startHidden) showSplash()

  const spaDir = join(process.resourcesPath, 'spa')
  const appIcon = assetPath(ASSET_ICON)
  backend = new BackendProcess({
    spaDir,
    appIcon: appIcon ?? undefined,
    onUnexpectedExit: (reason) => {
      void handleBackendCrash(reason)
    },
  })

  await startBackendWithRecovery()
  if (quitting.value || !backend?.info) return
  createMainWindow()
  createTray()
  void refreshTrayMenu()
}

// ---------------------------------------------------------------------------
// Backend
// ---------------------------------------------------------------------------

async function startBackendWithRecovery(): Promise<void> {
  if (!backend) return
  try {
    await backend.start()
  } catch (err) {
    closeSplash()
    const message = err instanceof Error ? err.message : String(err)
    log.error(`backend não iniciou: ${message}`)
    if (quitting.value) return
    const choice = await dialog.showMessageBox({
      type: 'error',
      title: 'Free Games Hub',
      message: 'Não foi possível iniciar o serviço interno.',
      detail: message,
      buttons: ['Tentar novamente', 'Sair'],
      defaultId: 0,
      cancelId: 1,
      noLink: true,
    })
    if (choice.response === 0) {
      return startBackendWithRecovery()
    }
    quitApp()
  }
}

async function handleBackendCrash(reason: string): Promise<void> {
  if (quitting.value) return
  closeSplash()
  const choice = await dialog.showMessageBox({
    type: 'error',
    title: 'Free Games Hub',
    message: 'O serviço interno parou de responder.',
    detail: reason,
    buttons: ['Reiniciar serviço', 'Sair'],
    defaultId: 0,
    cancelId: 1,
    noLink: true,
  })
  if (choice.response !== 0) {
    quitApp()
    return
  }

  try {
    const info = await backend?.restart()
    if (!info) throw new Error('backend indisponível')
    log.info(`backend reiniciado na porta ${info.port}`)
    if (mainWindow && !mainWindow.isDestroyed()) {
      await mainWindow.loadURL(`http://127.0.0.1:${info.port}/`)
      showMainWindow()
    } else {
      createMainWindow()
    }
    void refreshTrayMenu()
  } catch (err) {
    void handleBackendCrash(
      err instanceof Error ? err.message : String(err),
    )
  }
}

// ---------------------------------------------------------------------------
// Janela
// ---------------------------------------------------------------------------

function createMainWindow(): void {
  if (!backend?.info) {
    showFatalError('Free Games Hub', 'O serviço interno não está disponível.')
    return
  }

  const state = loadWindowState()
  const icon = assetPath(ASSET_ICON)

  mainWindow = new BrowserWindow({
    ...state.bounds,
    minWidth: 1000,
    minHeight: 640,
    show: false,
    backgroundColor: '#F7F7F5',
    title: 'Free Games Hub',
    icon: icon ?? undefined,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  })

  if (state.maximized) mainWindow.maximize()
  trackWindowState(mainWindow)

  mainWindow.once('ready-to-show', () => {
    closeSplash()
    if (!startHidden) mainWindow?.show()
  })

  mainWindow.on('close', (event) => {
    if (quitting.value) return
    event.preventDefault()
    void handleCloseRequested()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!isAllowedOrigin(url)) event.preventDefault()
  })
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    openExternal(url)
    return { action: 'deny' }
  })
  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    log.error(`renderer encerrado: ${details.reason} (${details.exitCode})`)
    void handleRendererGone()
  })

  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    void mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void mainWindow.loadURL(`http://127.0.0.1:${backend.info.port}/`)
  }
}

async function handleCloseRequested(): Promise<void> {
  let closeToTray = true
  try {
    const settings = await backend?.json<{ close_to_tray?: boolean }>('/api/settings')
    closeToTray = settings?.close_to_tray ?? true
  } catch {
    // backend indisponível: mantém o comportamento padrão (ocultar)
  }

  // Sem bandeja (ex.: Linux sem AppIndicator), esconder deixaria o app sem
  // acesso; nesse caso encerra normalmente.
  if (closeToTray && tray !== null) {
    mainWindow?.hide()
  } else {
    quitApp()
  }
}

async function handleRendererGone(): Promise<void> {
  if (quitting.value || rendererRecoveryOpen) return
  rendererRecoveryOpen = true
  try {
    const choice = await dialog.showMessageBox({
      type: 'error',
      title: 'Free Games Hub',
      message: 'A interface parou de responder.',
      detail: 'Você pode recarregar a janela ou encerrar o aplicativo.',
      buttons: ['Recarregar', 'Sair'],
      defaultId: 0,
      cancelId: 1,
      noLink: true,
    })
    if (choice.response === 0) {
      mainWindow?.reload()
    } else {
      quitApp()
    }
  } finally {
    rendererRecoveryOpen = false
  }
}

function showMainWindow(): void {
  if (!mainWindow || mainWindow.isDestroyed()) {
    if (backend?.info) createMainWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

function quitApp(): void {
  if (quitting.value) return
  quitting.value = true
  backend?.stop()
  app.quit()
}

// ---------------------------------------------------------------------------
// Splash
// ---------------------------------------------------------------------------

function showSplash(): void {
  splashWindow = new BrowserWindow({
    width: 360,
    height: 220,
    frame: false,
    resizable: false,
    movable: false,
    show: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    backgroundColor: '#F7F7F5',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  splashShownAt = Date.now()
  splashWindow.once('ready-to-show', () => splashWindow?.show())
  void splashWindow.loadURL(splashDataUrl())
}

function closeSplash(): void {
  if (!splashWindow) return
  const elapsed = Date.now() - splashShownAt
  const delay = Math.max(0, 650 - elapsed)
  const current = splashWindow
  splashWindow = null
  setTimeout(() => {
    if (!current.isDestroyed()) current.close()
  }, delay).unref?.()
}

function splashDataUrl(): string {
  const html = `<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
<style>
  *{box-sizing:border-box} html,body{height:100%;margin:0}
  body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#F7F7F5;color:#18181B;
       display:flex;align-items:center;justify-content:center;user-select:none}
  .card{display:flex;flex-direction:column;align-items:center;gap:14px}
  .logo{width:56px;height:56px;border-radius:16px;background:#4F46E5;color:#fff;
        display:flex;align-items:center;justify-content:center;font-size:30px;box-shadow:0 8px 24px rgba(79,70,229,.28)}
  h1{font-size:16px;margin:0;font-weight:650;letter-spacing:-.01em}
  p{margin:0;font-size:12px;color:#71717A}
  .bar{width:140px;height:3px;border-radius:999px;background:#E7E5E4;overflow:hidden}
  .bar::after{content:'';display:block;width:45%;height:100%;border-radius:999px;background:#4F46E5;
              animation:slide 1.1s ease-in-out infinite}
  @keyframes slide{0%{transform:translateX(-100%)}100%{transform:translateX(320%)}}
</style></head>
<body><div class="card"><div class="logo">🎮</div><h1>Free Games Hub</h1>
<p>preparando seu monitor de ofertas…</p><div class="bar"></div></div></body></html>`
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`
}

// ---------------------------------------------------------------------------
// Bandeja
// ---------------------------------------------------------------------------

function createTray(): void {
  try {
    const iconPath = assetPath(ASSET_TRAY)
    const image = iconPath ? nativeImage.createFromPath(iconPath) : nativeImage.createEmpty()
    tray = new Tray(image)
    tray.setToolTip('Free Games Hub')
    tray.on('double-click', () => showMainWindow())
    tray.on('click', () => {
      if (process.platform === 'win32') showMainWindow()
    })
  } catch (err) {
    tray = null
    log.warn(`bandeja indisponível: ${String(err)}`)
  }
}

async function refreshTrayMenu(): Promise<void> {
  if (!tray) return
  try {
    const settings = await backend?.json<{ notifications_enabled?: boolean }>(
      '/api/settings',
    )
    trayNotifications = settings?.notifications_enabled ?? true
  } catch {
    // mantém o último valor conhecido
  }

  const autostart = getAutostart()
  trayAutostart = autostart.enabled
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: 'Abrir Free Games Hub', click: () => showMainWindow() },
      {
        label: 'Verificar agora',
        click: () => {
          void triggerCheckFromTray()
        },
      },
      { type: 'separator' },
      {
        label: 'Notificações',
        type: 'checkbox',
        checked: trayNotifications,
        click: (item) => {
          void setNotificationsFromTray(item.checked)
        },
      },
      {
        label: 'Iniciar com o sistema',
        type: 'checkbox',
        checked: trayAutostart,
        enabled: autostart.supported,
        click: (item) => {
          setAutostart(item.checked)
          void refreshTrayMenu()
        },
      },
      { type: 'separator' },
      { label: 'Sair', click: () => quitApp() },
    ]),
  )
}

async function triggerCheckFromTray(): Promise<void> {
  try {
    await backend?.json('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
    log.info('verificação manual solicitada pela bandeja')
  } catch (err) {
    log.warn(`verificação pela bandeja falhou: ${String(err)}`)
  }
}

async function setNotificationsFromTray(enabled: boolean): Promise<void> {
  try {
    await backend?.json('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notifications_enabled: enabled }),
    })
    trayNotifications = enabled
  } catch (err) {
    log.warn(`não foi possível alterar notificações: ${String(err)}`)
  }
  void refreshTrayMenu()
}

// ---------------------------------------------------------------------------
// IPC e segurança
// ---------------------------------------------------------------------------

function registerIpc(): void {
  ipcMain.handle('fgh:backend-info', (): BackendInfo | null => backend?.info ?? null)
  ipcMain.handle('fgh:app-info', () => ({
    version: app.getVersion(),
    platform: process.platform,
    packaged: app.isPackaged,
    logPath: log.path(),
  }))
  ipcMain.handle('fgh:open-external', (_event, url: unknown) => {
    if (typeof url !== 'string') throw new Error('url inválida')
    return openExternal(url)
  })
  ipcMain.handle('fgh:autostart-get', () => getAutostart())
  ipcMain.handle('fgh:autostart-set', (_event, enabled: unknown) => {
    if (typeof enabled !== 'boolean') throw new Error('valor inválido')
    const state = setAutostart(enabled)
    void refreshTrayMenu()
    return state
  })
  ipcMain.handle('fgh:open-data-dir', async () => {
    const folder = dataDir()
    mkdirSync(folder, { recursive: true })
    await shell.openPath(folder)
  })
  ipcMain.on('fgh:settings-changed', () => {
    void refreshTrayMenu()
  })
  ipcMain.on('fgh:quit', () => quitApp())
}

function configureSecurity(): void {
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => {
    callback(false)
  })
  session.defaultSession.setPermissionCheckHandler(() => false)

  if (app.isPackaged) {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      callback({
        responseHeaders: {
          ...details.responseHeaders,
          'Content-Security-Policy': [
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; " +
              "img-src 'self' data: https:; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; " +
              "font-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
          ],
        },
      })
    })
  }

  app.on('web-contents-created', (_event, contents) => {
    contents.on('will-attach-webview', (event) => event.preventDefault())
    contents.setWindowOpenHandler(({ url }) => {
      openExternal(url)
      return { action: 'deny' }
    })
  })
}

function isAllowedOrigin(url: string): boolean {
  const devUrl = process.env['ELECTRON_RENDERER_URL']
  if (!app.isPackaged && devUrl && url.startsWith(devUrl)) return true
  const info = backend?.info
  return info !== null && info !== undefined && url.startsWith(`http://127.0.0.1:${info.port}`)
}

async function openExternal(url: string): Promise<void> {
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    throw new Error('url inválida')
  }
  if (!['https:', 'http:', 'steam:'].includes(parsed.protocol)) {
    throw new Error('protocolo não permitido')
  }
  await shell.openExternal(url)
  return
}

function assetPath(name: string): string | null {
  const candidates = app.isPackaged
    ? [join(process.resourcesPath, 'assets', name)]
    : [join(app.getAppPath(), 'assets', name)]
  return candidates.find((candidate) => existsSync(candidate)) ?? null
}

function dataDir(): string {
  if (process.platform === 'win32') {
    return join(process.env.APPDATA ?? join(app.getPath('home'), 'AppData', 'Roaming'), 'FreeGamesHub')
  }
  return join(process.env.XDG_DATA_HOME ?? join(app.getPath('home'), '.local', 'share'), 'free-games-hub')
}

function showFatalError(title: string, detail: string): void {
  try {
    dialog.showErrorBox(title, detail)
  } catch {
    // sem UI disponível: o log já registrou o problema
  }
}

// Registra IPC imediatamente; os handlers consultam o estado atual.
registerIpc()
