import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { History as HistoryIcon, RefreshCw, Search } from 'lucide-react'

import { api } from '../lib/api'
import type { Post } from '../lib/types'
import { cn } from '../lib/cn'
import { openPost } from '../lib/open'
import { PostTable } from './PostTable'
import {
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
  inputClass,
  secondaryButtonClass,
} from './ui'

interface HistoryProps {
  notify: (message: string, tone?: 'success' | 'error' | 'info') => void
}

type Tab = 'all' | 'free' | 'library' | 'expired'

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'all', label: 'Todos' },
  { id: 'free', label: 'Grátis' },
  { id: 'library', label: 'Na biblioteca' },
  { id: 'expired', label: 'Expirados' },
]

export function History({ notify }: HistoryProps) {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('all')
  const [search, setSearch] = useState('')
  const [store, setStore] = useState('')

  const postsQuery = useQuery({
    queryKey: ['posts', 'history', search, store],
    queryFn: () =>
      api.posts({
        limit: 500,
        search: search.trim() || undefined,
        store: store || undefined,
      }),
  })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: api.stores })

  const priceCheckMutation = useMutation({
    mutationFn: () => api.check(true),
    onSuccess: (result) => {
      notify(
        result.started
          ? 'Verificação de preços iniciada.'
          : 'Já existe uma verificação em andamento.',
        'info',
      )
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const toggleMutation = useMutation({
    mutationFn: (post: Post) => api.setInLibrary(post.id, !post.in_library),
    onSuccess: (post) => {
      void queryClient.invalidateQueries({ queryKey: ['posts'] })
      void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
      notify(
        post.in_library
          ? 'Oferta marcada como resgatada.'
          : 'Oferta removida da biblioteca.',
      )
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const open = useCallback(
    (post: Post) => {
      void openPost(post).catch((err: unknown) =>
        notify(err instanceof Error ? err.message : String(err), 'error'),
      )
    },
    [notify],
  )

  const posts = useMemo(() => {
    const now = Date.now()
    return (postsQuery.data ?? []).filter((post) => {
      switch (tab) {
        case 'free':
          return post.price_status === 'free'
        case 'library':
          return post.in_library
        case 'expired':
          return post.ends_at !== null && new Date(post.ends_at).getTime() < now
        default:
          return true
      }
    })
  }, [postsQuery.data, tab])

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border bg-surface p-1">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              aria-pressed={tab === item.id}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-fast',
                tab === item.id
                  ? 'bg-accent-soft text-accent'
                  : 'text-ink-muted hover:bg-bg hover:text-ink',
              )}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="relative">
            <Search
              size={14}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint"
            />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar título…"
              className={cn(inputClass, 'w-56 pl-8')}
            />
          </label>
          <select
            value={store}
            onChange={(event) => setStore(event.target.value)}
            className={cn(inputClass, 'w-44')}
            aria-label="Filtrar por loja"
          >
            <option value="">Todas as lojas</option>
            {(storesQuery.data ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void postsQuery.refetch()}
            className={secondaryButtonClass}
            title="Atualizar histórico"
          >
            <RefreshCw size={14} className={postsQuery.isFetching ? 'animate-spin' : ''} />
            Atualizar
          </button>
          <button
            type="button"
            disabled={priceCheckMutation.isPending}
            onClick={() => priceCheckMutation.mutate()}
            className={secondaryButtonClass}
            title="Reconsultar preços de todas as ofertas pendentes"
          >
            <RefreshCw
              size={14}
              className={priceCheckMutation.isPending ? 'animate-spin' : ''}
            />
            Verificar preços
          </button>
        </div>
      </div>

      <p className="text-xs text-ink-muted">
        {posts.length} {posts.length === 1 ? 'oferta encontrada' : 'ofertas encontradas'}
        {search ? ` para “${search.trim()}”` : ''}
      </p>

      {postsQuery.isLoading ? (
        <LoadingBlock label="Carregando histórico…" />
      ) : postsQuery.isError ? (
        <ErrorBlock message={postsQuery.error.message} onRetry={() => void postsQuery.refetch()} />
      ) : posts.length === 0 ? (
        <EmptyBlock
          icon={<HistoryIcon size={18} />}
          title="Nada por aqui."
          description="Ofertas resgatadas, expiradas e verificações antigas aparecem neste histórico."
        />
      ) : (
        <PostTable
          posts={posts}
          onOpen={open}
          onToggleLibrary={(post) => toggleMutation.mutate(post)}
          busyId={toggleMutation.isPending ? (toggleMutation.variables?.id ?? null) : null}
        />
      )}
    </div>
  )
}
