import type { Post } from './types'

/** Formatação de datas e preços (pt-BR). */

function toDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const date = new Date(iso.includes('T') ? iso : `${iso}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

export function relativeTime(iso: string | null | undefined): string {
  const date = toDate(iso)
  if (!date) return 'nunca'
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.round(diffMs / 60_000)
  if (minutes < 1) return 'agora mesmo'
  if (minutes < 60) return `há ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `há ${hours} h`
  const days = Math.round(hours / 24)
  if (days < 30) return `há ${days} d`
  return date.toLocaleDateString('pt-BR')
}

export function formatDateTime(iso: string | null | undefined): string {
  const date = toDate(iso)
  if (!date) return '—'
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Texto para prazo futuro (ex.: "termina em 2 d"). */
export function untilTime(iso: string | null | undefined): string {
  const date = toDate(iso)
  if (!date) return ''
  const diffMs = date.getTime() - Date.now()
  if (diffMs <= 0) return 'expirado'
  const minutes = Math.max(1, Math.round(diffMs / 60_000))
  if (minutes < 60) return `termina em ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `termina em ${hours} h`
  const days = Math.round(hours / 24)
  if (days < 30) return `termina em ${days} d`
  return `termina em ${date.toLocaleDateString('pt-BR')}`
}

export function priceText(
  cents: number | null,
  currency: string | null | undefined,
): string {
  if (cents === null) return ''
  const code = currency?.toUpperCase() === 'USD' ? 'USD' : (currency?.toUpperCase() ?? 'BRL')
  const locale = code === 'USD' ? 'en-US' : 'pt-BR'
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency: code }).format(
      cents / 100,
    )
  } catch {
    return `${(cents / 100).toFixed(2)} ${code}`
  }
}

const STORE_LABELS: Record<string, string> = {
  steam: 'Steam',
  'epic-games-store': 'Epic Games',
  gog: 'GOG',
  itchio: 'Itch.io',
  'drm-free': 'DRM-Free',
  ubisoft: 'Ubisoft',
  battlenet: 'Battle.net',
  origin: 'EA App',
  'prime-gaming': 'Prime Gaming',
  stove: 'Stove',
  vr: 'VR',
  pc: 'PC',
  ps5: 'PlayStation 5',
  ps4: 'PlayStation 4',
  'xbox-series-xs': 'Xbox Series',
  'xbox-one': 'Xbox One',
  switch: 'Switch',
  android: 'Android',
  ios: 'iOS',
}

export function storeLabel(slug: string): string {
  return STORE_LABELS[slug] ?? slug
}

/** URL de abertura: resgate quando existir; Steam abre no cliente, se possível. */
export function postOpenUrl(post: Post): string | null {
  if (post.claim_url) return post.claim_url
  if (post.store === 'steam' && post.store_app_id) {
    return `steam://store/${post.store_app_id}`
  }
  return post.store_url || post.publication_url || null
}

export function statusLabel(post: Post): { label: string; tone: 'free' | 'muted' | 'accent' | 'warn' } | null {
  switch (post.price_status) {
    case 'free':
      return { label: 'Gratuito', tone: 'free' }
    case 'not_free':
      return { label: 'Pago', tone: 'muted' }
    case 'f2p':
      return { label: 'Free-to-play', tone: 'accent' }
    case 'unknown':
      return { label: 'Não verificado', tone: 'warn' }
    default:
      return null
  }
}
