import type { StoreInfo } from '../lib/types'
import { cn } from '../lib/cn'

interface StoreChipsProps {
  stores: StoreInfo[]
  /** Contagem de posts por loja (somente lojas com posts são exibidas). */
  counts: Record<string, number>
  /** Lojas desmarcadas pelo usuário (ocultas do grid). */
  excluded: Set<string>
  onToggle: (store: string) => void
  onSelectAll: () => void
  onClearAll: () => void
}

/**
 * Filtros rápidos por loja (paridade com a antiga `StoreFilterBar`):
 * chips checkáveis com contador, "Todas" e "Limpar".
 */
export function StoreChips({
  stores,
  counts,
  excluded,
  onToggle,
  onSelectAll,
  onClearAll,
}: StoreChipsProps) {
  const visible = stores.filter((s) => (counts[s.id] ?? 0) > 0)
  if (visible.length === 0) return null

  const allSelected = visible.every((s) => !excluded.has(s.id))
  const allExcluded = visible.every((s) => excluded.has(s.id))

  return (
    <div className="flex flex-wrap items-center gap-2">
      <FilterButton active={allSelected} onClick={onSelectAll} title="Mostrar todas as lojas">
        Todas
      </FilterButton>
      <FilterButton active={allExcluded} onClick={onClearAll} title="Ocultar todas as lojas">
        Limpar
      </FilterButton>
      <span className="mx-1 h-4 w-px bg-border" aria-hidden="true" />
      {visible.map((store) => {
        const active = !excluded.has(store.id)
        return (
          <button
            key={store.id}
            type="button"
            aria-pressed={active}
            title={active ? `Ocultar posts de ${store.label}` : `Mostrar posts de ${store.label}`}
            onClick={() => onToggle(store.id)}
            className={cn(
              'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-150',
              'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
              active
                ? 'border-border bg-surface text-ink'
                : 'border-border/60 bg-bg text-ink-faint line-through',
            )}
          >
            <span
              className={cn('size-1.5 rounded-full', active ? 'bg-free' : 'bg-ink-faint')}
            />
            {store.label}
            <span className={cn('tabular-nums', active ? 'text-ink-muted' : 'text-ink-faint')}>
              {counts[store.id]}
            </span>
          </button>
        )
      })}
    </div>
  )
}

function FilterButton({
  active,
  onClick,
  title,
  children,
}: {
  active: boolean
  onClick: () => void
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      title={title}
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-semibold transition-colors duration-150',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
        active
          ? 'border-accent/40 bg-accent/10 text-accent'
          : 'border-border bg-surface text-ink-muted hover:text-ink',
      )}
    >
      {children}
    </button>
  )
}
