import { Loader2, RefreshCw, Wifi, WifiOff } from 'lucide-react'

import { cn } from '../lib/cn'

interface TopBarProps {
  title: string
  description?: string
  checkRunning: boolean
  wsConnected: boolean
  onCheckNow: () => void
  checking: boolean
}

export function TopBar({
  title,
  description,
  checkRunning,
  wsConnected,
  onCheckNow,
  checking,
}: TopBarProps) {
  const busy = checkRunning || checking
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-6">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <h1 className="truncate text-base font-semibold">{title}</h1>
          <span
            className={cn(
              'flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium',
              wsConnected ? 'bg-free/10 text-free' : 'bg-warn/10 text-warn',
            )}
            title={wsConnected ? 'Eventos em tempo real conectados' : 'Tentando reconectar…'}
          >
            {wsConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {wsConnected ? 'ao vivo' : 'reconectando…'}
          </span>
        </div>
        {description && <p className="truncate text-xs text-ink-muted">{description}</p>}
      </div>

      <button
        type="button"
        onClick={onCheckNow}
        disabled={busy}
        className={cn(
          'flex shrink-0 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white',
          'transition-colors duration-fast hover:bg-accent/90',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
          busy && 'cursor-not-allowed opacity-60',
        )}
      >
        {busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
        {busy ? 'Verificando…' : 'Verificar agora'}
      </button>
    </header>
  )
}
