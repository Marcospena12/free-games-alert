import { spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

import { log } from './log'

export interface BackendInfo {
  port: number
  token: string
}

export interface BackendOptions {
  /** Diretório da SPA construída (produção). */
  spaDir?: string
  /** Ícone usado pelas notificações nativas (produção). */
  appIcon?: string
  /** Chamado quando o backend encerra sem ter sido solicitado. */
  onUnexpectedExit?: (reason: string) => void
}

const START_TIMEOUT_MS = 45_000
const HEALTH_TIMEOUT_MS = 45_000
const HEALTH_INTERVAL_MS = 250

export class BackendProcess {
  private child: ChildProcess | null = null
  private stopping = false
  private ready = false
  private token = ''
  private port = 0
  private stderrTail: string[] = []
  private generation = 0
  private options: BackendOptions

  constructor(options: BackendOptions = {}) {
    this.options = options
  }

  get info(): BackendInfo | null {
    return this.ready ? { port: this.port, token: this.token } : null
  }

  get baseUrl(): string | null {
    return this.ready ? `http://127.0.0.1:${this.port}` : null
  }

  async start(): Promise<BackendInfo> {
    if (this.ready) return { port: this.port, token: this.token }
    this.stopping = false
    this.stderrTail = []
    // Cada tentativa tem uma geração própria: eventos do processo antigo
    // (inclusive o exit durante um restart) não podem afetar o novo.
    const generation = ++this.generation
    const isDev = !app.isPackaged
    this.token = isDev ? '' : randomUUID()

    const { command, args } = isDev
      ? devCommand()
      : prodCommand(this.token, this.options.spaDir, this.options.appIcon)

    log.info(`iniciando backend: ${command} ${args.join(' ')}`)
    const child = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    })
    this.child = child

    const portPromise = new Promise<number>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`timeout esperando a porta do backend (${START_TIMEOUT_MS}ms)`))
      }, START_TIMEOUT_MS)
      let buffer = ''
      child.stdout?.on('data', (chunk: Buffer) => {
        buffer += chunk.toString()
        const lines = buffer.split(/\r?\n/)
        buffer = lines.pop() ?? ''
        for (const rawLine of lines) {
          const line = rawLine.trim()
          if (!line) continue
          const match = line.match(/^FGH_PORT=(\d+)$/)
          if (match) {
            clearTimeout(timer)
            resolve(Number(match[1]))
          } else {
            log.info(`[backend] ${line}`)
          }
        }
      })
      child.stderr?.on('data', (chunk: Buffer) => {
        const text = chunk.toString().trim()
        if (!text) return
        for (const line of text.split(/\r?\n/)) {
          if (!line.trim()) continue
          this.stderrTail.push(line)
          if (this.stderrTail.length > 20) this.stderrTail.shift()
          log.warn(`[backend] ${line}`)
        }
      })
      child.once('error', (err) => {
        clearTimeout(timer)
        reject(new Error(`falha ao iniciar o backend: ${err.message}`))
      })
      child.once('exit', (code, signal) => {
        if (generation !== this.generation) return
        clearTimeout(timer)
        if (!this.ready) {
          const tail = this.stderrTail.slice(-5).join(' | ')
          reject(
            new Error(
              `backend terminou antes de ficar pronto (código ${code ?? signal ?? '?'})${tail ? `: ${tail}` : ''}`,
            ),
          )
        }
      })
    })

    let port: number
    try {
      port = await portPromise
    } catch (err) {
      this.stop()
      throw err instanceof Error ? err : new Error(String(err))
    }
    this.port = port

    try {
      await waitForHealth(port, this.token)
    } catch (err) {
      this.stop()
      throw err instanceof Error ? err : new Error(String(err))
    }

    this.ready = true
    log.info(`backend pronto em http://127.0.0.1:${port}`)

    child.once('exit', (code, signal) => {
      if (generation !== this.generation) return
      const wasReady = this.ready
      this.ready = false
      this.child = null
      if (this.stopping || !wasReady) return
      const reason = `O backend encerrou inesperadamente (código ${code ?? signal ?? '?'}).`
      log.error(reason)
      this.options.onUnexpectedExit?.(reason)
    })

    return { port, token: this.token }
  }

  async restart(): Promise<BackendInfo> {
    this.stop()
    return this.start()
  }

  stop(): void {
    this.stopping = true
    this.ready = false
    this.generation += 1
    const child = this.child
    this.child = null
    if (!child || child.exitCode !== null) return
    const pid = child.pid
    if (pid === undefined) return

    log.info(`encerrando backend (pid ${pid})`)
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(pid), '/T', '/F'], {
        windowsHide: true,
        stdio: 'ignore',
      })
      return
    }

    try {
      child.kill('SIGTERM')
    } catch {
      // já encerrou
    }
    const timer = setTimeout(() => {
      try {
        child.kill('SIGKILL')
      } catch {
        // já encerrou
      }
    }, 3_000)
    timer.unref?.()
  }

  async request(path: string, init?: RequestInit): Promise<Response> {
    if (!this.ready) throw new Error('backend indisponível')
    const headers: Record<string, string> = {
      ...(this.token ? { 'X-FGH-Token': this.token } : {}),
      ...(init?.headers as Record<string, string> | undefined),
    }
    return fetch(`http://127.0.0.1:${this.port}${path}`, {
      ...init,
      headers,
    })
  }

  async json<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await this.request(path, init)
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null
      throw new Error(body?.detail ?? `HTTP ${response.status}`)
    }
    return (await response.json()) as T
  }
}

function devCommand(): { command: string; args: string[] } {
  const isWin = process.platform === 'win32'
  // Venv do repositório (raiz), se existir — garante as dependências do backend.
  const venvPython = isWin
    ? join(app.getAppPath(), '..', '.venv', 'Scripts', 'python.exe')
    : join(app.getAppPath(), '..', '.venv', 'bin', 'python')
  const command = existsSync(venvPython) ? venvPython : isWin ? 'python' : 'python3'
  return {
    command,
    args: ['-m', 'free_games_hub.api', '--dev', '--port', '0'],
  }
}

function prodCommand(
  token: string,
  spaDir?: string,
  appIcon?: string,
): { command: string; args: string[] } {
  const isWin = process.platform === 'win32'
  const exe = isWin ? 'free-games-hub-backend.exe' : 'free-games-hub-backend'
  const base = process.resourcesPath
  const command = join(base, exe)
  if (!existsSync(command)) {
    throw new Error(`backend não encontrado em ${command}`)
  }
  if (!spaDir || !existsSync(join(spaDir, 'index.html'))) {
    throw new Error(`SPA não encontrada em ${spaDir ?? '(vazio)'}`)
  }
  const args = ['--port', '0', '--token', token, '--spa-dir', spaDir]
  if (appIcon && existsSync(appIcon)) args.push('--app-icon', appIcon)
  return { command, args }
}

async function waitForHealth(port: number, token: string): Promise<void> {
  const url = `http://127.0.0.1:${port}/health`
  const deadline = Date.now() + HEALTH_TIMEOUT_MS
  for (;;) {
    try {
      const res = await fetch(url, {
        headers: token ? { 'X-FGH-Token': token } : {},
      })
      if (res.ok) return
    } catch {
      // servidor ainda não aceitou conexões
    }
    if (Date.now() > deadline) {
      throw new Error(`backend não respondeu em ${HEALTH_TIMEOUT_MS}ms`)
    }
    await new Promise((resolve) => setTimeout(resolve, HEALTH_INTERVAL_MS))
  }
}
