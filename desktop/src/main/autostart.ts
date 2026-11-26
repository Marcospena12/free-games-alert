import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

import { app } from 'electron'

import { log } from './log'

const RUN_KEY = String.raw`Software\Microsoft\Windows\CurrentVersion\Run`
// Valor usado pela versão 0.3+ (mesmo nome exibido no Gerenciador de Tarefas).
const WINDOWS_VALUE = 'Free Games Hub'
const LEGACY_WINDOWS_VALUES = ['FreeGamesHub', 'SteamFreeGamesMonitor']
const INSTALLER_STATE_KEY = String.raw`Software\FreeGamesHub`

const LINUX_FILENAME = 'free-games-hub.desktop'
const LEGACY_LINUX_FILENAMES = [
  'FreeGamesHub.desktop',
  'freegameshub.desktop',
  'steam-free-games-monitor.desktop',
]

export interface AutostartState {
  supported: boolean
  enabled: boolean
  reason?: string
}

function configHome(): string {
  return process.env.XDG_CONFIG_HOME || join(homedir(), '.config')
}

function autostartDir(): string {
  return join(configHome(), 'autostart')
}

function linuxFile(): string {
  return join(autostartDir(), LINUX_FILENAME)
}

function linuxEntryPath(): string {
  // Em AppImage, `process.execPath` aponta para o ponto de montagem temporário.
  const appImage = process.env.APPIMAGE
  return appImage && appImage.length > 0 ? appImage : process.execPath
}

function quoteExec(path: string): string {
  return `"${path.replace(/(["\\$`])/g, '\\$1')}"`
}

function windowsCommand(): string {
  return `"${process.execPath}" --hidden`
}

function reg(args: string[]): { ok: boolean; output: string } {
  const result = spawnSync('reg.exe', args, {
    windowsHide: true,
    encoding: 'utf-8',
  })
  return {
    ok: result.status === 0,
    output: result.stdout ?? '',
  }
}

function readWindowsValue(name: string): string | null {
  const { ok, output } = reg(['query', `HKCU\\${RUN_KEY}`, '/v', name])
  if (!ok) return null
  for (const line of output.split(/\r?\n/)) {
    const match = line.match(/REG_SZ\s+(.*)$/)
    if (match) return match[1].trim()
  }
  return null
}

function writeWindowsValue(name: string, value: string): boolean {
  const { ok } = reg([
    'add',
    `HKCU\\${RUN_KEY}`,
    '/v',
    name,
    '/t',
    'REG_SZ',
    '/d',
    value,
    '/f',
  ])
  return ok
}

function deleteWindowsValue(name: string): void {
  reg(['delete', `HKCU\\${RUN_KEY}`, '/v', name, '/f'])
}

export function autostartSupported(): boolean {
  if (!app.isPackaged) return false
  return process.platform === 'win32' || process.platform === 'linux'
}

export function getAutostart(): AutostartState {
  if (!app.isPackaged) {
    return {
      supported: false,
      enabled: false,
      reason: 'Disponível apenas na versão instalada.',
    }
  }

  if (process.platform === 'win32') {
    return { supported: true, enabled: readWindowsValue(WINDOWS_VALUE) !== null }
  }

  if (process.platform === 'linux') {
    return { supported: true, enabled: existsSync(linuxFile()) }
  }

  return {
    supported: false,
    enabled: false,
    reason: 'Inicialização automática não é suportada nesta plataforma.',
  }
}

export function setAutostart(enabled: boolean): AutostartState {
  if (!app.isPackaged) {
    return getAutostart()
  }

  if (process.platform === 'win32') {
    if (enabled) {
      if (!writeWindowsValue(WINDOWS_VALUE, windowsCommand())) {
        throw new Error('Não foi possível gravar a inicialização automática.')
      }
    } else {
      deleteWindowsValue(WINDOWS_VALUE)
    }
    return getAutostart()
  }

  if (process.platform === 'linux') {
    const file = linuxFile()
    if (!enabled) {
      rmSync(file, { force: true })
      return getAutostart()
    }
    mkdirSync(autostartDir(), { recursive: true })
    const executable = linuxEntryPath()
    const content = [
      '[Desktop Entry]',
      'Type=Application',
      'Version=1.0',
      'Name=Free Games Hub',
      'Comment=Monitor de jogos gratuitos',
      `Exec=${quoteExec(executable)} --hidden`,
      `TryExec=${executable}`,
      'Terminal=false',
      'X-GNOME-Autostart-enabled=true',
      'X-GNOME-Autostart-Delay=3',
      'Categories=Utility;',
      '',
    ].join('\n')
    writeFileSync(file, content, 'utf-8')
    return getAutostart()
  }

  return getAutostart()
}

/**
 * Migra/remove entradas de inicialização automática da versão antiga.
 *
 * - Windows: se a 0.2.0 tinha autostart e a 0.3 ainda não tem, preserva a
 *   preferência criando o valor novo; depois remove o valor legado. O
 *   instalador NSIS faz o mesmo caminho antes de desinstalar a 0.2.0.
 * - Linux: a versão antiga não tinha instalador oficial; remove arquivos
 *   .desktop residuais.
 */
export function cleanupLegacyAutostart(): void {
  if (process.platform === 'win32') {
    if (!app.isPackaged) return
    let migrated = false
    for (const name of LEGACY_WINDOWS_VALUES) {
      const legacy = readWindowsValue(name)
      if (legacy === null) continue
      if (readWindowsValue(WINDOWS_VALUE) === null) {
        if (writeWindowsValue(WINDOWS_VALUE, windowsCommand())) {
          migrated = true
          log.info(`autostart legado migrado (${name} -> ${WINDOWS_VALUE})`)
        }
      }
      deleteWindowsValue(name)
      log.info(`entrada de autostart legada removida: ${name}`)
    }

    // O instalador grava esse marcador antes de rodar o desinstalador antigo.
    reg(['delete', `HKCU\\${INSTALLER_STATE_KEY}`, '/v', 'LegacyAutostart', '/f'])
    if (migrated) {
      log.info('preferência de autostart da versão antiga preservada')
    }
    return
  }

  if (process.platform !== 'linux') return
  for (const name of LEGACY_LINUX_FILENAMES) {
    const file = join(autostartDir(), name)
    if (!existsSync(file)) continue
    try {
      rmSync(file, { force: true })
      log.info(`entrada de autostart legada removida: ${file}`)
    } catch (err) {
      log.warn(`não foi possível remover ${file}: ${String(err)}`)
    }
  }
}
