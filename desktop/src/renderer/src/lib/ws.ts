import { useEffect, useRef, useState } from 'react'

import type { WsEvent } from './types'

interface WsState {
  connected: boolean
  lastEvent: WsEvent | null
}

/**
 * Conecta ao WebSocket do backend com reconexão automática (backoff até 15s).
 * O callback é estável entre renders (via ref), então a conexão não cai.
 */
export function useWs(onEvent: (event: WsEvent) => void): WsState {
  const [state, setState] = useState<WsState>({ connected: false, lastEvent: null })
  const callbackRef = useRef(onEvent)
  callbackRef.current = onEvent

  useEffect(() => {
    let ws: WebSocket | null = null
    let timer: number | undefined
    let closed = false
    let attempts = 0

    const connect = async (): Promise<void> => {
      const info = await window.fgh.getBackendInfo()
      if (closed) return
      if (!info) {
        timer = window.setTimeout(connect, 2_000)
        return
      }
      const { port, token } = info
      const url = `ws://127.0.0.1:${port}/ws${token ? `?token=${encodeURIComponent(token)}` : ''}`
      ws = new WebSocket(url)
      ws.onopen = () => {
        attempts = 0
        setState((s) => ({ ...s, connected: true }))
      }
      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as WsEvent
          setState((s) => ({ ...s, lastEvent: event }))
          callbackRef.current(event)
        } catch {
          // mensagem não-JSON: ignora
        }
      }
      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }))
        if (!closed) {
          attempts += 1
          const delay = Math.min(15_000, 500 * 2 ** attempts)
          timer = window.setTimeout(connect, delay)
        }
      }
      ws.onerror = () => ws?.close()
    }

    void connect()

    return () => {
      closed = true
      if (timer !== undefined) window.clearTimeout(timer)
      ws?.close()
    }
  }, [])

  return state
}
