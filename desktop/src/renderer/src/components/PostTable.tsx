import { Check, ExternalLink, Loader2, RotateCcw } from 'lucide-react'

import type { Post } from '../lib/types'
import { cn } from '../lib/cn'
import {
  formatDateTime,
  priceText,
  statusLabel,
  storeLabel,
  untilTime,
} from '../lib/format'

interface PostTableProps {
  posts: Post[]
  onOpen: (post: Post) => void
  onToggleLibrary?: (post: Post) => void
  busyId?: number | null
}

const TONE_CLASS: Record<string, string> = {
  free: 'bg-free/10 text-free',
  muted: 'bg-bg text-ink-muted',
  accent: 'bg-accent-soft text-accent',
  warn: 'bg-warn/10 text-warn',
}

export function PostTable({ posts, onOpen, onToggleLibrary, busyId }: PostTableProps) {
  return (
    <div className="overflow-x-auto rounded-card border border-border bg-surface shadow-card">
      <table className="w-full min-w-[820px] text-left text-sm">
        <thead className="border-b border-border bg-bg/60 text-[11px] uppercase tracking-wide text-ink-faint">
          <tr>
            <th className="px-4 py-2.5 font-medium">Título</th>
            <th className="px-4 py-2.5 font-medium">Loja</th>
            <th className="px-4 py-2.5 font-medium">Origem</th>
            <th className="px-4 py-2.5 font-medium">Preço</th>
            <th className="px-4 py-2.5 font-medium">Detectado</th>
            <th className="px-4 py-2.5 font-medium">Prazo</th>
            <th className="px-4 py-2.5 text-right font-medium">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {posts.map((post) => {
            const badge = statusLabel(post)
            const busy = busyId === post.id
            return (
              <tr key={post.id} className="align-middle transition-colors duration-fast hover:bg-bg/50">
                <td className="max-w-[360px] px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium" title={post.title}>
                      {post.title}
                    </span>
                    {post.in_library && (
                      <span className="shrink-0 rounded-full bg-accent-soft px-1.5 py-0.5 text-[10px] font-medium text-accent">
                        biblioteca
                      </span>
                    )}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 text-xs text-ink-muted">
                  {storeLabel(post.store)}
                </td>
                <td className="max-w-[160px] truncate px-4 py-2.5 text-xs text-ink-muted">
                  {post.group_name ?? '—'}
                </td>
                <td className="whitespace-nowrap px-4 py-2.5">
                  {badge ? (
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-[11px] font-semibold',
                        TONE_CLASS[badge.tone],
                      )}
                    >
                      {badge.label}
                    </span>
                  ) : post.price_final_cents != null ? (
                    <span className="text-xs">{priceText(post.price_final_cents, post.price_currency)}</span>
                  ) : (
                    <span className="text-xs text-ink-faint">—</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 text-xs text-ink-muted">
                  {formatDateTime(post.discovered_at)}
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 text-xs">
                  {post.ends_at ? (
                    <span className={cn(new Date(post.ends_at).getTime() < Date.now() && 'text-danger')}>
                      {untilTime(post.ends_at)}
                    </span>
                  ) : (
                    <span className="text-ink-faint">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center justify-end gap-1.5">
                    <button
                      type="button"
                      onClick={() => onOpen(post)}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-accent transition-colors duration-fast hover:bg-accent-soft"
                    >
                      <ExternalLink size={12} />
                      Abrir
                    </button>
                    {onToggleLibrary && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => onToggleLibrary(post)}
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-ink-muted transition-colors duration-fast hover:bg-bg hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {busy ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : post.in_library ? (
                          <RotateCcw size={12} />
                        ) : (
                          <Check size={12} />
                        )}
                        {post.in_library ? 'Remover' : 'Já resgatei'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
