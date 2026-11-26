import { motion } from 'framer-motion'
import { Gift, History, Layers, Users } from 'lucide-react'

import type { Snapshot } from '../lib/types'
import { relativeTime } from '../lib/format'

interface MetricsProps {
  snapshot: Snapshot
}

export function Metrics({ snapshot }: MetricsProps) {
  const items = [
    {
      label: 'Gratuitos agora',
      value: snapshot.free_now,
      icon: Gift,
      tone: 'text-free bg-free/10',
    },
    {
      label: 'Posts no total',
      value: snapshot.total_posts,
      icon: History,
      tone: 'text-accent bg-accent-soft',
    },
    {
      label: 'Grupos ativos',
      value: `${snapshot.groups.active} / ${snapshot.groups.total}`,
      icon: Users,
      tone: 'text-ink-muted bg-bg',
    },
    {
      label: 'Última verificação',
      value: relativeTime(snapshot.last_checked_at),
      icon: Layers,
      tone: 'text-ink-muted bg-bg',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
      {items.map(({ label, value, icon: Icon, tone }) => (
        <motion.div
          key={label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="rounded-card border border-border bg-surface p-4 shadow-card"
        >
          <div className="flex items-center gap-3">
            <div className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${tone}`}>
              <Icon size={18} />
            </div>
            <div className="min-w-0">
              <p className="text-xl font-semibold leading-tight">{value}</p>
              <p className="truncate text-xs text-ink-muted">{label}</p>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
