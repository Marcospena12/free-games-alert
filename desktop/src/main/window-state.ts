import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app, screen, type BrowserWindow, type Rectangle } from 'electron'

import { log } from './log'

export interface WindowState {
  bounds: Rectangle
  maximized: boolean
}

const DEFAULT_STATE: WindowState = {
  bounds: { x: 0, y: 0, width: 1400, height: 900 },
  maximized: false,
}

function stateFile(): string {
  return join(app.getPath('userData'), 'window-state.json')
}

function intersects(a: Rectangle, b: Rectangle): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  )
}

function isUsable(bounds: Rectangle): boolean {
  if (bounds.width < 900 || bounds.height < 600) return false
  return screen.getAllDisplays().some((display) => intersects(bounds, display.workArea))
}

export function loadWindowState(): WindowState {
  try {
    const parsed = JSON.parse(readFileSync(stateFile(), 'utf-8')) as Partial<WindowState>
    if (
      parsed.bounds &&
      Number.isFinite(parsed.bounds.x) &&
      Number.isFinite(parsed.bounds.y) &&
      Number.isFinite(parsed.bounds.width) &&
      Number.isFinite(parsed.bounds.height) &&
      isUsable(parsed.bounds)
    ) {
      return { bounds: parsed.bounds, maximized: Boolean(parsed.maximized) }
    }
  } catch {
    // arquivo ausente ou inválido: usa o padrão
  }
  return { ...DEFAULT_STATE, bounds: { ...DEFAULT_STATE.bounds } }
}

export function trackWindowState(window: BrowserWindow): void {
  let timer: NodeJS.Timeout | undefined

  const save = (): void => {
    if (window.isDestroyed()) return
    const state: WindowState = {
      bounds: window.getNormalBounds(),
      maximized: window.isMaximized(),
    }
    try {
      writeFileSync(stateFile(), JSON.stringify(state), 'utf-8')
    } catch (err) {
      log.warn(`não foi possível salvar o estado da janela: ${String(err)}`)
    }
  }

  const schedule = (): void => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(save, 400)
  }

  window.on('resize', schedule)
  window.on('move', schedule)
  window.on('maximize', schedule)
  window.on('unmaximize', schedule)
  window.on('close', () => {
    if (timer) clearTimeout(timer)
    save()
  })
}
