import { appendFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'

import { app } from 'electron'

let logFile: string | null = null

function resolveLogFile(): string | null {
  if (logFile) return logFile
  try {
    logFile = join(app.getPath('userData'), 'desktop.log')
    mkdirSync(dirname(logFile), { recursive: true })
  } catch {
    logFile = null
  }
  return logFile
}

type Level = 'info' | 'warn' | 'error'

function write(level: Level, message: string): void {
  const line = `${new Date().toISOString()} ${level.toUpperCase()} ${message}`
  if (level === 'error') console.error(line)
  else if (level === 'warn') console.warn(line)
  else console.log(line)

  const file = resolveLogFile()
  if (!file) return
  try {
    appendFileSync(file, `${line}\n`, 'utf-8')
  } catch {
    // Log em arquivo é melhor esforço; nunca deve derrubar o app.
  }
}

export const log = {
  info: (message: string) => write('info', message),
  warn: (message: string) => write('warn', message),
  error: (message: string) => write('error', message),
  path: () => resolveLogFile(),
}
