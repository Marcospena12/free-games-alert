import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Info, Loader2, X } from 'lucide-react'

import { api, initApi } from './lib/api'
import { cn } from './lib/cn'
import { hashForPage, PAGE_TITLES, pageFromHash, type Page } from './lib/nav'
import { useWs } from './lib/ws'
import { Dashboard } from './components/Dashboard'
import { Groups } from './components/Groups'
import { History } from './components/History'
import { SettingsPage } from './components/SettingsPage'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { ErrorBlock, LoadingBlock } from './components/ui'

type BootState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready' }

type Tone = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  tone: Tone
}

const PAGE_DESCRIPTIONS: Record<Page, string> = {
  dashboard: 'Ofertas 100% grátis e ativas neste momento.',
  history: 'Tudo o que o monitor já encontrou, incluindo ofertas resgatadas e expiradas.',
  groups: 'Feeds RSS monitorados e o estado de cada fonte.',
  settings: 'Preferências, filtros por loja e diagnóstico.',
}

export default function App() {
  const queryClient = useQueryClient()
  const [boot, setBoot] = useState<BootState>({ status: 'loading' })
  const [page, setPage] = useState<Page>(() => pageFromHash(window.location.hash))
  const [checking, setChecking] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const toastTimer = useRef<number | undefined>(undefined)

  const notify = useCallback((message: string, tone: Tone = 'success') => {
    if (toastTimer.current !== undefined) window.clearTimeout(toastTimer.current)
    setToast({ id: Date.now(), message, tone })
    toastTimer.current = window.setTimeout(() => setToast(null), 4_500)
  }, [])

  useEffect(() => {
    return () => {
      if (toastTimer.current !== undefined) window.clearTimeout(toastTimer.current)
    }
  }, [])

  useEffect(() => {
    const onHashChange = (): void => setPage(pageFromHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        await initApi()
        if (!cancelled) setBoot({ status: 'ready' })
      } catch (err) {
        if (!cancelled) {
          setBoot({
            status: 'error',
            message: err instanceof Error ? err.message : String(err),
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const snapshotQuery = useQuery({
    queryKey: ['snapshot'],
    queryFn: api.snapshot,
    enabled: boot.status === 'ready',
    refetchInterval: 60_000,
  })

  const invalidateAll = useCallback(() => {
    void queryClient.invalidateQueries()
  }, [queryClient])

  const ws = useWs(
    useCallback(
      (event) => {
        if (event.type === 'check.started') setChecking(true)
        if (event.type === 'check.finished') {
          setChecking(false)
          invalidateAll()
        }
        if (event.type === 'check.failed') {
          setChecking(false)
          invalidateAll()
          const message =
            typeof event.data.message === 'string'
              ? event.data.message
              : 'A verificação falhou.'
          notify(message, 'error')
        }
        if (
          event.type === 'posts.updated' ||
          event.type === 'groups.updated' ||
          event.type === 'settings.updated'
        ) {
          invalidateAll()
        }
      },
      [invalidateAll, notify],
    ),
  )

  const checkMutation = useMutation({
    mutationFn: () => api.check(false),
    onSuccess: (data) => {
      if (data.started) {
        setChecking(true)
        void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
      } else {
        setChecking(false)
        notify('Já existe uma verificação em andamento.', 'info')
      }
    },
    onError: (err) => {
      setChecking(false)
      notify(err.message, 'error')
    },
  })

  const navigate = useCallback((next: Page) => {
    if (window.location.hash !== hashForPage(next)) {
      window.location.hash = hashForPage(next)
    }
    setPage(next)
  }, [])

  if (boot.status === 'loading') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-ink-muted">
        <Loader2 size={20} className="animate-spin text-accent" />
        Conectando ao serviço interno…
      </div>
    )
  }

  if (boot.status === 'error') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
        <AlertCircle size={22} className="text-danger" />
        <div>
          <p className="text-sm font-medium text-danger">Não foi possível conectar ao backend</p>
          <p className="mt-1 max-w-lg text-xs text-ink-muted">{boot.message}</p>
        </div>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium hover:bg-bg"
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  const snapshot = snapshotQuery.data
  const checkRunning = (snapshot?.check_running ?? false) || checking

  return (
    <div className="flex h-full overflow-hidden">
      <Sidebar
        page={page}
        onNavigate={navigate}
        lastCheckedAt={snapshot?.last_checked_at ?? null}
        checkIntervalMinutes={snapshot?.settings.check_interval_minutes ?? 5}
        freeCount={snapshot?.free_now ?? 0}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title={PAGE_TITLES[page]}
          description={PAGE_DESCRIPTIONS[page]}
          checkRunning={checkRunning}
          wsConnected={ws.connected}
          checking={checkMutation.isPending}
          onCheckNow={() => checkMutation.mutate()}
        />

        <main className="flex-1 overflow-y-auto px-6 py-6">
          {page === 'dashboard' ? (
            snapshotQuery.isLoading ? (
              <LoadingBlock label="Carregando painel…" />
            ) : snapshotQuery.isError ? (
              <ErrorBlock
                message={snapshotQuery.error.message}
                onRetry={() => void snapshotQuery.refetch()}
              />
            ) : snapshot ? (
              <Dashboard snapshot={snapshot} notify={notify} />
            ) : (
              <LoadingBlock label="Carregando painel…" />
            )
          ) : page === 'history' ? (
            <History notify={notify} />
          ) : page === 'groups' ? (
            <Groups notify={notify} />
          ) : (
            <SettingsPage notify={notify} checkRunning={checkRunning} />
          )}
        </main>
      </div>

      {toast && <ToastView toast={toast} onClose={() => setToast(null)} />}
    </div>
  )
}

function ToastView({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const tone =
    toast.tone === 'error'
      ? { icon: AlertCircle, className: 'border-danger/30 bg-danger/10 text-danger' }
      : toast.tone === 'info'
        ? { icon: Info, className: 'border-accent/25 bg-accent-soft text-accent' }
        : { icon: CheckCircle2, className: 'border-free/25 bg-free/10 text-free' }
  const Icon = tone.icon
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'fixed bottom-5 right-5 z-50 flex max-w-sm items-start gap-3 rounded-card border px-4 py-3 text-sm shadow-pop',
        tone.className,
      )}
    >
      <Icon size={16} className="mt-0.5 shrink-0" />
      <p className="flex-1 leading-snug">{toast.message}</p>
      <button
        type="button"
        onClick={onClose}
        aria-label="Fechar aviso"
        className="rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
      >
        <X size={14} />
      </button>
    </div>
  )
}
