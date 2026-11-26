import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, CheckCircle2, ExternalLink, Gamepad2, Gift, Loader2, Tag } from 'lucide-react'

import type { Post } from '../lib/types'
import { cn } from '../lib/cn'
import {
  priceText,
  relativeTime,
  statusLabel,
  storeLabel,
  untilTime,
} from '../lib/format'

interface PostCardProps {
  post: Post
  index: number
  onOpen: (post: Post) => void
  onMarkInLibrary?: (post: Post) => void
  busy?: boolean
}

const TONE_CLASS: Record<string, string> = {
  free: 'bg-free/10 text-free',
  muted: 'bg-bg text-ink-muted',
  accent: 'bg-accent-soft text-accent',
  warn: 'bg-warn/10 text-warn',
}

export function PostCard({ post, index, onOpen, onMarkInLibrary, busy = false }: PostCardProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const badge = statusLabel(post)
  const hasDiscount =
    post.price_initial_cents !== null &&
    post.price_final_cents !== null &&
    post.price_initial_cents > post.price_final_cents
  const claim = post.claim_url !== null

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut', delay: Math.min(index * 0.03, 0.3) }}
      className="group flex flex-col overflow-hidden rounded-card border border-border bg-surface shadow-card transition-shadow duration-base hover:shadow-pop"
    >
      <button
        type="button"
        onClick={() => onOpen(post)}
        className="relative aspect-video w-full overflow-hidden bg-bg text-left focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
        aria-label={`Abrir ${post.title}`}
      >
        {post.image_url && !imageFailed ? (
          <img
            src={post.image_url}
            alt=""
            loading="lazy"
            onError={() => setImageFailed(true)}
            className="size-full object-cover transition-transform duration-base group-hover:scale-[1.02]"
          />
        ) : (
          <span className="flex size-full items-center justify-center text-ink-faint">
            <Gamepad2 size={30} />
          </span>
        )}
        {badge && (
          <span
            className={cn(
              'absolute left-2 top-2 rounded-full px-2.5 py-1 text-[11px] font-semibold',
              TONE_CLASS[badge.tone],
            )}
          >
            {badge.label}
          </span>
        )}
        {post.in_library && (
          <span
            title="Na minha biblioteca"
            className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-full bg-ink/70 text-white"
          >
            <CheckCircle2 size={15} />
          </span>
        )}
      </button>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="min-w-0 flex-1 text-sm font-semibold leading-snug" title={post.title}>
            {post.title}
          </h3>
          <span className="shrink-0 rounded bg-bg px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">
            {storeLabel(post.store)}
          </span>
        </div>

        {post.group_name && <p className="truncate text-xs text-ink-faint">{post.group_name}</p>}

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <div className="flex min-w-0 items-baseline gap-1.5">
            {hasDiscount ? (
              <>
                <span className="text-xs text-ink-faint line-through">
                  {priceText(post.price_initial_cents, post.price_currency)}
                </span>
                <span className="text-sm font-semibold text-free">
                  {priceText(post.price_final_cents, post.price_currency)}
                </span>
                {post.price_discount_percent != null && (
                  <span className="flex items-center gap-0.5 text-[11px] font-medium text-warn">
                    <Tag size={11} />-{post.price_discount_percent}%
                  </span>
                )}
              </>
            ) : post.price_status === 'free' ? (
              <span className="text-sm font-semibold text-free">Grátis</span>
            ) : post.price_final_cents != null ? (
              <span className="text-sm font-semibold">
                {priceText(post.price_final_cents, post.price_currency)}
              </span>
            ) : (
              <span className="text-xs text-ink-faint">sem preço</span>
            )}
          </div>

          <span className="shrink-0 text-[11px] text-ink-faint">
            {post.ends_at ? untilTime(post.ends_at) : relativeTime(post.discovered_at)}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 border-t border-border px-4 py-2.5">
        <button
          type="button"
          onClick={() => onOpen(post)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-accent/10 py-1.5 text-xs font-semibold text-accent transition-colors duration-fast hover:bg-accent/15"
        >
          {claim ? <Gift size={13} /> : <ExternalLink size={13} />}
          {claim ? 'Resgatar' : 'Abrir'}
        </button>
        {onMarkInLibrary && !post.in_library && (
          <button
            type="button"
            disabled={busy}
            onClick={() => onMarkInLibrary(post)}
            className="flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-ink-muted transition-colors duration-fast hover:bg-bg hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
            title="Marcar como já adicionado à biblioteca"
          >
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
            Já resgatei
          </button>
        )}
      </div>
    </motion.article>
  )
}
