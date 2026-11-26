import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LayoutGrid, List, RefreshCw } from 'lucide-react'

import { api } from '../lib/api'
import type { Post, Snapshot, StoreInfo } from '../lib/types'
import { cn } from '../lib/cn'
import { openPost } from '../lib/open'
import { Metrics } from './Metrics'
import { StoreChips } from './StoreChips'
import { PostCard } from './PostCard'
import { PostTable } from './PostTable'
import { EmptyBlock, ErrorBlock, LoadingBlock, smallButtonClass } from './ui'

interface DashboardProps {
  snapshot: Snapshot
  notify: (message: string, tone?: 'success' | 'error' | 'info') => void
}

type ViewMode = 'cards' | 'list'
const VIEW_KEY = 'fgh:dashboard-view'

export function Dashboard({ snapshot, notify }: DashboardProps) {
  const queryClient = useQueryClient()
  const [excluded, setExcluded] = useState<Set<string>>(() => new Set())
  const [view, setView] = useState<ViewMode>(() =>
    localStorage.getItem(VIEW_KEY) === 'list' ? 'list' : 'cards',
  )

  const postsQuery = useQuery({
    queryKey: ['posts', 'dashboard'],
    queryFn: () => api.posts({ limit: 100, status: 'free', library: false, active: true }),
  })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: api.stores })

  const markMutation = useMutation({
    mutationFn: (post: Post) => api.setInLibrary(post.id, true),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['posts'] })
      void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
      notify('Oferta marcada como resgatada e movida para o histórico.')
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

  const posts = postsQuery.data ?? []
  const storeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const post of posts) counts[post.store] = (counts[post.store] ?? 0) + 1
    return counts
  }, [posts])
  const visiblePosts = useMemo(
    () => posts.filter((post) => !excluded.has(post.store)),
    [posts, excluded],
  )

  const toggleStore = useCallback((store: string) => {
    setExcluded((prev) => {
      const next = new Set(prev)
      if (next.has(store)) next.delete(store)
      else next.add(store)
      return next
    })
  }, [])
  const selectAllStores = useCallback(() => setExcluded(new Set()), [])
  const clearAllStores = useCallback(() => {
    setExcluded(new Set(Object.keys(storeCounts)))
  }, [storeCounts])

  const changeView = (mode: ViewMode): void => {
    setView(mode)
    localStorage.setItem(VIEW_KEY, mode)
  }

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6">
      <Metrics snapshot={snapshot} />

      {storesQuery.data && (
        <StoreChips
          stores={storesQuery.data as StoreInfo[]}
          counts={storeCounts}
          excluded={excluded}
          onToggle={toggleStore}
          onSelectAll={selectAllStores}
          onClearAll={clearAllStores}
        />
      )}

      <section>
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold">Ofertas grátis agora</h2>
            <p className="text-xs text-ink-muted">
              Somente ofertas ativas e que ainda não estão na sua biblioteca.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-faint">
              {posts.length > 0
                ? `${visiblePosts.length} de ${posts.length} exibidos`
                : 'nenhuma oferta'}
            </span>
            <div className="flex items-center rounded-lg border border-border bg-surface p-0.5">
              <button
                type="button"
                title="Exibir em cards"
                aria-pressed={view === 'cards'}
                onClick={() => changeView('cards')}
                className={cn(
                  'rounded-md p-1.5 transition-colors duration-fast',
                  view === 'cards' ? 'bg-accent-soft text-accent' : 'text-ink-faint hover:text-ink',
                )}
              >
                <LayoutGrid size={15} />
              </button>
              <button
                type="button"
                title="Exibir em lista"
                aria-pressed={view === 'list'}
                onClick={() => changeView('list')}
                className={cn(
                  'rounded-md p-1.5 transition-colors duration-fast',
                  view === 'list' ? 'bg-accent-soft text-accent' : 'text-ink-faint hover:text-ink',
                )}
              >
                <List size={15} />
              </button>
            </div>
          </div>
        </div>

        {postsQuery.isLoading ? (
          <LoadingBlock label="Carregando ofertas…" />
        ) : postsQuery.isError ? (
          <ErrorBlock
            message={postsQuery.error.message}
            onRetry={() => void postsQuery.refetch()}
          />
        ) : posts.length === 0 ? (
          <EmptyBlock
            icon={<RefreshCw size={18} />}
            title="Nenhuma oferta grátis ativa."
            description="Clique em “Verificar agora” para buscar nas fontes."
          />
        ) : visiblePosts.length === 0 ? (
          <EmptyBlock
            title="Nenhuma oferta com os filtros atuais."
            action={
              <button type="button" onClick={selectAllStores} className={smallButtonClass}>
                Mostrar todas as lojas
              </button>
            }
          />
        ) : view === 'cards' ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {visiblePosts.map((post, index) => (
              <PostCard
                key={post.id}
                post={post}
                index={index}
                onOpen={open}
                onMarkInLibrary={(item) => markMutation.mutate(item)}
                busy={markMutation.isPending && markMutation.variables?.id === post.id}
              />
            ))}
          </div>
        ) : (
          <PostTable
            posts={visiblePosts}
            onOpen={open}
            onToggleLibrary={(item) => markMutation.mutate(item)}
            busyId={markMutation.isPending ? (markMutation.variables?.id ?? null) : null}
          />
        )}
      </section>
    </div>
  )
}
