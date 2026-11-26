import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  Loader2,
  Pencil,
  Plus,
  Rss,
  Trash2,
  Users,
  X,
} from 'lucide-react'

import { api } from '../lib/api'
import type { Group } from '../lib/types'
import { cn } from '../lib/cn'
import { formatDateTime } from '../lib/format'
import {
  EmptyBlock,
  ErrorBlock,
  Field,
  LoadingBlock,
  Section,
  inputClass,
  primaryButtonClass,
  secondaryButtonClass,
  smallButtonClass,
} from './ui'

interface GroupsProps {
  notify: (message: string, tone?: 'success' | 'error' | 'info') => void
}

interface GroupDraft {
  name: string
  url: string
}

const EMPTY_DRAFT: GroupDraft = { name: '', url: '' }

export function Groups({ notify }: GroupsProps) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<GroupDraft>(EMPTY_DRAFT)
  const [editingId, setEditingId] = useState<number | null>(null)

  const groupsQuery = useQuery({ queryKey: ['groups'], queryFn: api.groups })

  const invalidate = (): void => {
    void queryClient.invalidateQueries({ queryKey: ['groups'] })
    void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const name = draft.name.trim()
      const url = draft.url.trim()
      if (!name || !url) throw new Error('Informe nome e URL do feed.')
      if (!/^https?:\/\//i.test(url)) throw new Error('A URL deve começar com http:// ou https://.')
      if (editingId === null) return api.createGroup({ name, url, active: true })
      const group = groupsQuery.data?.find((item) => item.id === editingId)
      return api.updateGroup(editingId, { name, url, active: group?.active ?? true })
    },
    onSuccess: () => {
      notify(editingId === null ? 'Fonte adicionada.' : 'Fonte atualizada.')
      setDraft(EMPTY_DRAFT)
      setEditingId(null)
      invalidate()
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const toggleMutation = useMutation({
    mutationFn: (group: Group) =>
      api.updateGroup(group.id, {
        name: group.name,
        url: group.url,
        active: !group.active,
      }),
    onSuccess: (group) => {
      notify(group.active ? 'Fonte ativada.' : 'Fonte pausada.')
      invalidate()
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (group: Group) => api.deleteGroup(group.id),
    onSuccess: () => {
      notify('Fonte removida.')
      invalidate()
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const startEdit = (group: Group): void => {
    setEditingId(group.id)
    setDraft({ name: group.name, url: group.url })
  }

  const cancelEdit = (): void => {
    setEditingId(null)
    setDraft(EMPTY_DRAFT)
  }

  const requestDelete = (group: Group): void => {
    const confirmed = window.confirm(
      `Remover a fonte “${group.name}”?\nAs ofertas já registradas permanecem no histórico.`,
    )
    if (confirmed) deleteMutation.mutate(group)
  }

  const groups = groupsQuery.data ?? []

  return (
    <div className="mx-auto flex max-w-[1100px] flex-col gap-5">
      <Section
        title={editingId === null ? 'Adicionar fonte RSS' : 'Editar fonte RSS'}
        description="Feeds da comunidade Steam ou qualquer RSS compatível com o formato do monitor."
      >
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(event) => {
            event.preventDefault()
            saveMutation.mutate()
          }}
        >
          <Field label="Nome" className="sm:w-64">
            <input
              className={inputClass}
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              placeholder="Comunidade Jogos Brasil"
              autoComplete="off"
            />
          </Field>
          <Field label="URL do feed" className="flex-1">
            <input
              className={inputClass}
              value={draft.url}
              onChange={(event) => setDraft({ ...draft, url: event.target.value })}
              placeholder="https://steamcommunity.com/groups/…/rss/"
              autoComplete="off"
              inputMode="url"
            />
          </Field>
          <div className="flex items-center gap-2">
            <button type="submit" disabled={saveMutation.isPending} className={primaryButtonClass}>
              {saveMutation.isPending ? (
                <Loader2 size={15} className="animate-spin" />
              ) : editingId === null ? (
                <Plus size={15} />
              ) : (
                <Check size={15} />
              )}
              {editingId === null ? 'Adicionar' : 'Salvar'}
            </button>
            {editingId !== null && (
              <button type="button" onClick={cancelEdit} className={secondaryButtonClass}>
                <X size={15} />
                Cancelar
              </button>
            )}
          </div>
        </form>
      </Section>

      <Section
        title="Fontes monitoradas"
        description={`${groups.filter((group) => group.active).length} ativas de ${groups.length} cadastradas.`}
      >
        {groupsQuery.isLoading ? (
          <LoadingBlock label="Carregando fontes…" />
        ) : groupsQuery.isError ? (
          <ErrorBlock message={groupsQuery.error.message} onRetry={() => void groupsQuery.refetch()} />
        ) : groups.length === 0 ? (
          <EmptyBlock
            icon={<Rss size={18} />}
            title="Nenhuma fonte cadastrada."
            description="Adicione um feed RSS acima para começar a monitorar ofertas."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {groups.map((group) => (
              <li
                key={group.id}
                className={cn(
                  'flex flex-col gap-3 rounded-lg border border-border px-4 py-3 sm:flex-row sm:items-center',
                  !group.active && 'bg-bg/60',
                )}
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <div
                    className={cn(
                      'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg',
                      group.active ? 'bg-accent-soft text-accent' : 'bg-bg text-ink-faint',
                    )}
                  >
                    <Users size={15} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium">{group.name}</p>
                      {!group.active && (
                        <span className="rounded-full bg-bg px-2 py-0.5 text-[10px] text-ink-faint">
                          pausada
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-ink-muted" title={group.url}>
                      {group.url}
                    </p>
                    <p className="mt-0.5 text-[11px] text-ink-faint">
                      última verificação: {formatDateTime(group.last_checked_at)}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-1.5 self-end sm:self-center">
                  <button
                    type="button"
                    disabled={toggleMutation.isPending}
                    onClick={() => toggleMutation.mutate(group)}
                    className={smallButtonClass}
                    title={group.active ? 'Pausar fonte' : 'Ativar fonte'}
                  >
                    {toggleMutation.isPending && toggleMutation.variables?.id === group.id ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <span
                        className={cn(
                          'size-1.5 rounded-full',
                          group.active ? 'bg-free' : 'bg-ink-faint',
                        )}
                      />
                    )}
                    {group.active ? 'Ativa' : 'Pausada'}
                  </button>
                  <button
                    type="button"
                    onClick={() => startEdit(group)}
                    className={smallButtonClass}
                    title="Editar fonte"
                  >
                    <Pencil size={12} />
                    Editar
                  </button>
                  <button
                    type="button"
                    disabled={deleteMutation.isPending}
                    onClick={() => requestDelete(group)}
                    className={cn(smallButtonClass, 'hover:border-danger/30 hover:bg-danger/5 hover:text-danger')}
                    title="Remover fonte"
                  >
                    {deleteMutation.isPending && deleteMutation.variables?.id === group.id ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Trash2 size={12} />
                    )}
                    Remover
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}
