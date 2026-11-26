import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Gamepad2,
  History,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Users,
} from 'lucide-react'

import { cn } from '../lib/cn'
import type { Page } from '../lib/nav'
import { relativeTime } from '../lib/format'

interface SidebarProps {
  page: Page
  onNavigate: (page: Page) => void
  lastCheckedAt: string | null
  checkIntervalMinutes: number
  freeCount: number
}

const NAV_ITEMS: Array<{ id: Page; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'dashboard', label: 'Painel', icon: LayoutDashboard },
  { id: 'history', label: 'Histórico', icon: History },
  { id: 'groups', label: 'Grupos', icon: Users },
  { id: 'settings', label: 'Configurações', icon: Settings },
]

export function Sidebar({
  page,
  onNavigate,
  lastCheckedAt,
  checkIntervalMinutes,
  freeCount,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 240 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="flex h-full shrink-0 flex-col border-r border-border bg-surface"
    >
      <div
        className={cn(
          'flex h-16 items-center gap-3 border-b border-border px-4',
          collapsed && 'justify-center px-0',
        )}
      >
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-white">
          <Gamepad2 size={18} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold leading-tight">Free Games Hub</p>
            <p className="text-[11px] leading-tight text-ink-muted">monitor de jogos grátis</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Navegação principal">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = page === id
          return (
            <button
              key={id}
              type="button"
              title={label}
              aria-current={active ? 'page' : undefined}
              onClick={() => onNavigate(id)}
              className={cn(
                'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-fast',
                'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
                active
                  ? 'bg-accent-soft font-medium text-accent'
                  : 'text-ink-muted hover:bg-bg hover:text-ink',
                collapsed && 'justify-center px-0',
              )}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span className="flex-1 text-left">{label}</span>}
              {!collapsed && id === 'dashboard' && freeCount > 0 && (
                <span className="rounded-full bg-free/10 px-2 py-0.5 text-[10px] font-semibold tabular-nums text-free">
                  {freeCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      <div className="border-t border-border p-3">
        {!collapsed && (
          <div className="mb-2 rounded-lg bg-bg px-3 py-2">
            <p className="text-[11px] font-medium text-ink-muted">Verificações</p>
            <p className="text-[11px] leading-relaxed text-ink-faint">
              a cada {checkIntervalMinutes} min
              <br />
              última: {relativeTime(lastCheckedAt)}
            </p>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className={cn(
            'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-muted transition-colors duration-fast hover:bg-bg hover:text-ink',
            collapsed && 'justify-center px-0',
          )}
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          {!collapsed && <span>Recolher</span>}
        </button>
      </div>
    </motion.aside>
  )
}
