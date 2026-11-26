import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Bell,
  Check,
  Copy,
  FolderOpen,
  Info,
  Loader2,
  RefreshCw,
  Save,
  Send,
  Server,
  ShieldCheck,
} from 'lucide-react'

import { api } from '../lib/api'
import type { Settings, StoreFilterConfig, StoreInfo } from '../lib/types'
import { cn } from '../lib/cn'
import { formatDateTime, storeLabel } from '../lib/format'
import {
  ErrorBlock,
  Field,
  LoadingBlock,
  Section,
  Toggle,
  inputClass,
  primaryButtonClass,
  secondaryButtonClass,
  smallButtonClass,
} from './ui'

interface SettingsPageProps {
  notify: (message: string, tone?: 'success' | 'error' | 'info') => void
  checkRunning: boolean
}

const TYPE_OPTIONS = [
  { id: 'game', label: 'Jogos completos' },
  { id: 'loot', label: 'DLCs e itens' },
  { id: 'beta', label: 'Betas / acesso antecipado' },
  { id: 'other', label: 'Outros' },
]

function defaultFilter(): StoreFilterConfig {
  return {
    enabled: true,
    allowed_types: ['game'],
    min_worth_usd: null,
    include_na_worth: true,
    title_include_keywords: [],
    title_exclude_keywords: [],
    ignore_no_end_date: false,
    min_hours_before_expiration: null,
  }
}

function parseKeywords(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
}

export function SettingsPage({ notify, checkRunning }: SettingsPageProps) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Settings | null>(null)
  const [dirty, setDirty] = useState(false)
  const [selectedStore, setSelectedStore] = useState('steam')

  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: api.settings })
  const errorsQuery = useQuery({ queryKey: ['errors'], queryFn: () => api.errors(50) })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: api.stores })
  const aboutQuery = useQuery({ queryKey: ['about'], queryFn: api.about })
  const appInfoQuery = useQuery({ queryKey: ['app-info'], queryFn: () => window.fgh.getAppInfo() })
  const autostartQuery = useQuery({ queryKey: ['autostart'], queryFn: () => window.fgh.getAutostart() })

  useEffect(() => {
    if (settingsQuery.data && (!dirty || draft === null)) {
      setDraft(settingsQuery.data)
      setDirty(false)
    }
  }, [settingsQuery.data, dirty, draft])

  useEffect(() => {
    if (!selectedStore && storesQuery.data && storesQuery.data.length > 0) {
      setSelectedStore(storesQuery.data[0].id)
    }
  }, [selectedStore, storesQuery.data])

  const update = (patch: Partial<Settings>): void => {
    setDraft((current) => (current ? { ...current, ...patch } : current))
    setDirty(true)
  }

  const updateFilter = (slug: string, patch: Partial<StoreFilterConfig>): void => {
    if (!draft) return
    const current = draft.store_filters[slug] ?? defaultFilter()
    setDraft({
      ...draft,
      store_filters: {
        ...draft.store_filters,
        [slug]: { ...current, ...patch },
      },
    })
    setDirty(true)
  }

  const saveMutation = useMutation({
    mutationFn: (payload: Settings) => {
      // A interface edita as regras por loja; enviar os campos globais
      // legados (`stores_enabled`/`enabled_types`) sobrescreveria o que o
      // usuário acabou de configurar em cada loja.
      return api.updateSettings({
        check_interval_minutes: payload.check_interval_minutes,
        notifications_enabled: payload.notifications_enabled,
        close_to_tray: payload.close_to_tray,
        gamerpower_enabled: payload.gamerpower_enabled,
        store_filters: payload.store_filters,
      })
    },
    onSuccess: (saved) => {
      setDraft(saved)
      setDirty(false)
      void queryClient.invalidateQueries({ queryKey: ['settings'] })
      void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
      void queryClient.invalidateQueries({ queryKey: ['stores'] })
      window.fgh.settingsChanged()
      notify('Configurações salvas.')
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const testMutation = useMutation({
    mutationFn: api.testNotification,
    onSuccess: () => notify('Notificação de teste enviada.', 'info'),
    onError: (err) => notify(err.message, 'error'),
  })

  const checkMutation = useMutation({
    mutationFn: (forcePrices: boolean) => api.check(forcePrices),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['snapshot'] })
      notify('Verificação iniciada.', 'info')
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const autostartMutation = useMutation({
    mutationFn: (enabled: boolean) => window.fgh.setAutostart(enabled),
    onSuccess: (state) => {
      queryClient.setQueryData(['autostart'], state)
      notify(state.enabled ? 'Inicialização automática ativada.' : 'Inicialização automática desativada.')
    },
    onError: (err) => notify(err.message, 'error'),
  })

  const storeOptions = useMemo<StoreInfo[]>(() => storesQuery.data ?? [], [storesQuery.data])
  const selectedInfo = storeOptions.find((store) => store.id === selectedStore)
  const filter = draft?.store_filters[selectedStore] ?? defaultFilter()
  const autostart = autostartQuery.data

  const copyFilterToAll = (): void => {
    if (!draft) return
    const next: Record<string, StoreFilterConfig> = { ...draft.store_filters }
    const slugs = new Set([...Object.keys(next), ...storeOptions.map((store) => store.id)])
    for (const slug of slugs) {
      const config = next[slug] ?? defaultFilter()
      next[slug] = {
        ...config,
        allowed_types: [...filter.allowed_types],
        min_worth_usd: filter.min_worth_usd,
        include_na_worth: filter.include_na_worth,
        title_include_keywords: [...filter.title_include_keywords],
        title_exclude_keywords: [...filter.title_exclude_keywords],
        ignore_no_end_date: filter.ignore_no_end_date,
        min_hours_before_expiration: filter.min_hours_before_expiration,
      }
    }
    setDraft({ ...draft, store_filters: next })
    setDirty(true)
    notify('Critérios copiados para todas as lojas. Salve para aplicar.', 'info')
  }

  if (settingsQuery.isError) {
    return (
      <ErrorBlock
        message={settingsQuery.error.message}
        onRetry={() => void settingsQuery.refetch()}
      />
    )
  }

  if (settingsQuery.isLoading || !draft) {
    return <LoadingBlock label="Carregando configurações…" />
  }

  const busy = checkMutation.isPending || checkRunning

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-ink-muted">
          {dirty ? 'Há alterações não salvas.' : 'Tudo salvo.'}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void settingsQuery.refetch()}
            className={secondaryButtonClass}
          >
            <RefreshCw size={14} />
            Recarregar
          </button>
          <button
            type="button"
            disabled={!dirty || saveMutation.isPending}
            onClick={() => saveMutation.mutate(draft)}
            className={primaryButtonClass}
          >
            {saveMutation.isPending ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Save size={15} />
            )}
            Salvar alterações
          </button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex flex-col gap-5">
          <Section title="Monitoramento" description="Intervalo e comportamento do aplicativo.">
            <div className="flex flex-col gap-1">
              <Field
                label="Intervalo entre verificações"
                hint="Mínimo de 1 minuto. O agendador lê este valor a cada ciclo."
                className="max-w-xs px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={1440}
                    value={draft.check_interval_minutes}
                    onChange={(event) => {
                      const value = Number.parseInt(event.target.value, 10)
                      if (Number.isFinite(value)) update({ check_interval_minutes: Math.max(1, value) })
                    }}
                    className={inputClass}
                  />
                  <span className="text-xs text-ink-muted">min</span>
                </div>
              </Field>

              <Toggle
                checked={draft.notifications_enabled}
                onChange={(checked) => update({ notifications_enabled: checked })}
                label="Notificar novas ofertas gratuitas"
                description="Mostra alertas nativos quando uma oferta 100% grátis é confirmada."
              />
              <Toggle
                checked={draft.close_to_tray}
                onChange={(checked) => update({ close_to_tray: checked })}
                label="Fechar a janela para a bandeja"
                description="Ao fechar, o monitor continua rodando em segundo plano."
              />
              <Toggle
                checked={autostart?.enabled ?? false}
                onChange={(checked) => autostartMutation.mutate(checked)}
                disabled={!autostart?.supported || autostartMutation.isPending}
                label="Iniciar com o sistema"
                description={
                  autostart?.supported
                    ? 'Abre minimizado na bandeja junto com o sistema.'
                    : (autostart?.reason ?? 'Disponível apenas na versão instalada.')
                }
              />
            </div>

            <div className="mt-3 flex flex-wrap gap-2 border-t border-border px-3 pt-4">
              <button
                type="button"
                disabled={busy}
                onClick={() => checkMutation.mutate(false)}
                className={primaryButtonClass}
              >
                {busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
                Verificar agora
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => checkMutation.mutate(true)}
                className={secondaryButtonClass}
              >
                <RefreshCw size={15} />
                Forçar verificação de preços
              </button>
              <button
                type="button"
                disabled={testMutation.isPending}
                onClick={() => testMutation.mutate()}
                className={secondaryButtonClass}
              >
                {testMutation.isPending ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <Send size={15} />
                )}
                Testar notificação
              </button>
            </div>
          </Section>

          <Section
            title="Fontes e filtros por loja"
            description="A GamerPower complementa os feeds RSS. Cada loja tem regras próprias."
          >
            <Toggle
              checked={draft.gamerpower_enabled}
              onChange={(checked) => update({ gamerpower_enabled: checked })}
              label="Habilitar GamerPower API"
              description="Monitoramento multi-loja em uma única consulta pública."
            />

            <div className="mt-4 flex flex-col gap-3 rounded-lg border border-border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <label className="text-xs font-medium text-ink-muted" htmlFor="store-select">
                  Loja:
                </label>
                <select
                  id="store-select"
                  className={cn(inputClass, 'w-56')}
                  value={selectedStore}
                  onChange={(event) => setSelectedStore(event.target.value)}
                >
                  {storeOptions.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.label}
                    </option>
                  ))}
                  {storeOptions.length === 0 && (
                    <option value="steam">{storeLabel('steam')}</option>
                  )}
                </select>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={filter.enabled}
                    onChange={(event) => updateFilter(selectedStore, { enabled: event.target.checked })}
                    className="size-4 accent-accent"
                  />
                  Monitorar esta loja
                </label>
                <button type="button" onClick={copyFilterToAll} className={smallButtonClass}>
                  <Copy size={12} />
                  Copiar para todas
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                {TYPE_OPTIONS.map((type) => (
                  <label key={type.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={filter.allowed_types.includes(type.id)}
                      onChange={(event) => {
                        const next = new Set(filter.allowed_types)
                        if (event.target.checked) next.add(type.id)
                        else next.delete(type.id)
                        updateFilter(selectedStore, {
                          allowed_types: next.size > 0 ? [...next] : ['game'],
                        })
                      }}
                      className="size-4 accent-accent"
                    />
                    {type.label}
                  </label>
                ))}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Valor mínimo estimado (USD)" hint="0 ou vazio desativa o filtro.">
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={filter.min_worth_usd ?? ''}
                    onChange={(event) => {
                      const raw = event.target.value.trim()
                      updateFilter(selectedStore, {
                        min_worth_usd: raw === '' ? null : Math.max(0, Number(raw)),
                      })
                    }}
                    className={inputClass}
                    placeholder="Sem valor mínimo"
                  />
                </Field>
                <Field label="Horas mínimas antes de expirar" hint="Vazio desativa o filtro.">
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={filter.min_hours_before_expiration ?? ''}
                    onChange={(event) => {
                      const raw = event.target.value.trim()
                      updateFilter(selectedStore, {
                        min_hours_before_expiration: raw === '' ? null : Math.max(0, Number(raw)),
                      })
                    }}
                    className={inputClass}
                    placeholder="Sem mínimo"
                  />
                </Field>
              </div>

              <Field
                label="Palavras a excluir"
                hint="Separe por vírgula. Ex.: demo, trial, prologue."
              >
                <input
                  value={filter.title_exclude_keywords.join(', ')}
                  onChange={(event) =>
                    updateFilter(selectedStore, {
                      title_exclude_keywords: parseKeywords(event.target.value),
                    })
                  }
                  className={inputClass}
                  placeholder="demo, trial, prologue"
                />
              </Field>
              <Field
                label="Palavras obrigatórias (opcional)"
                hint="A oferta precisa conter ao menos uma destas palavras."
              >
                <input
                  value={filter.title_include_keywords.join(', ')}
                  onChange={(event) =>
                    updateFilter(selectedStore, {
                      title_include_keywords: parseKeywords(event.target.value),
                    })
                  }
                  className={inputClass}
                  placeholder="deixe vazio para aceitar todas"
                />
              </Field>

              <div className="flex flex-wrap gap-x-5 gap-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={filter.include_na_worth}
                    onChange={(event) =>
                      updateFilter(selectedStore, { include_na_worth: event.target.checked })
                    }
                    className="size-4 accent-accent"
                  />
                  Aceitar ofertas sem valor informado
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={filter.ignore_no_end_date}
                    onChange={(event) =>
                      updateFilter(selectedStore, { ignore_no_end_date: event.target.checked })
                    }
                    className="size-4 accent-accent"
                  />
                  Ignorar ofertas sem data de término
                </label>
              </div>
            </div>

            {selectedInfo && (
              <p className="mt-3 text-[11px] text-ink-faint">
                {filter.enabled ? 'Loja ativa' : 'Loja desativada'} · dados de ofertas multicanal
                fornecidos por GamerPower.com
              </p>
            )}
          </Section>

          <Section
            title="Erros recentes"
            description="Falhas registradas pelo monitoramento (as últimas 50)."
            actions={
              <button
                type="button"
                onClick={() => void errorsQuery.refetch()}
                className={smallButtonClass}
              >
                <RefreshCw size={12} className={errorsQuery.isFetching ? 'animate-spin' : ''} />
                Atualizar
              </button>
            }
          >
            {errorsQuery.isLoading ? (
              <LoadingBlock label="Carregando erros…" />
            ) : errorsQuery.isError ? (
              <ErrorBlock
                message={errorsQuery.error.message}
                onRetry={() => void errorsQuery.refetch()}
              />
            ) : (errorsQuery.data ?? []).length === 0 ? (
              <div className="flex items-center gap-2 rounded-lg bg-free/5 px-3 py-3 text-sm text-free">
                <Check size={16} />
                Nenhum erro registrado até o momento.
              </div>
            ) : (
              <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto">
                {(errorsQuery.data ?? []).map((error) => (
                  <li key={error.id} className="rounded-lg border border-border px-3 py-2">
                    <div className="flex items-start gap-2">
                      <AlertTriangle size={14} className="mt-0.5 shrink-0 text-warn" />
                      <div className="min-w-0">
                        <p className="text-sm">{error.message}</p>
                        <p className="mt-0.5 text-[11px] text-ink-faint">
                          {formatDateTime(error.created_at)}
                          {error.group_name ? ` · ${error.group_name}` : ''}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>

        <div className="flex flex-col gap-5">
          <Section title="Sobre" description="Informações da instalação e do serviço local.">
            <dl className="flex flex-col gap-3 text-sm">
              <InfoRow label="Aplicativo" value={appInfoQuery.data?.version ?? '—'} />
              <InfoRow label="API" value={aboutQuery.data?.version ?? '—'} />
              <InfoRow label="Python" value={aboutQuery.data?.python ?? '—'} />
              <InfoRow
                label="Plataforma"
                value={appInfoQuery.data?.platform ?? aboutQuery.data?.platform ?? '—'}
              />
              <InfoRow
                label="Banco de dados"
                value={aboutQuery.data?.db_path ?? '—'}
                wrap
              />
              <InfoRow
                label="Log"
                value={aboutQuery.data?.log_path ?? appInfoQuery.data?.logPath ?? '—'}
                wrap
              />
            </dl>
            <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
              <button
                type="button"
                onClick={() =>
                  void window.fgh
                    .openDataDir()
                    .catch((err: unknown) =>
                      notify(err instanceof Error ? err.message : String(err), 'error'),
                    )
                }
                className={secondaryButtonClass}
              >
                <FolderOpen size={14} />
                Abrir pasta de dados
              </button>
              <button
                type="button"
                disabled={dirty}
                onClick={() => saveMutation.mutate(draft)}
                className={secondaryButtonClass}
                title={dirty ? 'Salve as alterações antes de sair' : 'Salvar'}
              >
                <Save size={14} />
                Salvar
              </button>
            </div>
          </Section>

          <Section title="Status" description="Resumo rápido do serviço e das fontes.">
            <ul className="flex flex-col gap-2 text-sm">
              <StatusRow
                icon={<Server size={15} />}
                label="Serviço interno"
                value={aboutQuery.isError ? 'indisponível' : 'conectado'}
                ok={!aboutQuery.isError}
              />
              <StatusRow
                icon={<Bell size={15} />}
                label="Notificações"
                value={draft.notifications_enabled ? 'ativadas' : 'desativadas'}
                ok={draft.notifications_enabled}
              />
              <StatusRow
                icon={<ShieldCheck size={15} />}
                label="Fechar para bandeja"
                value={draft.close_to_tray ? 'sim' : 'não'}
                ok={draft.close_to_tray}
              />
              <StatusRow
                icon={<Info size={15} />}
                label="Verificação"
                value={checkRunning ? 'em andamento' : 'ociosa'}
                ok={!checkRunning}
              />
            </ul>
          </Section>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value, wrap = false }: { label: string; value: string; wrap?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">{label}</dt>
      <dd className={cn('mt-0.5 font-mono text-xs text-ink-muted', wrap && 'break-all')}>
        {value}
      </dd>
    </div>
  )
}

function StatusRow({
  icon,
  label,
  value,
  ok,
}: {
  icon: ReactNode
  label: string
  value: string
  ok: boolean
}) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg bg-bg/60 px-3 py-2">
      <span className="flex items-center gap-2 text-xs text-ink-muted">
        {icon}
        {label}
      </span>
      <span className={cn('text-xs font-medium', ok ? 'text-free' : 'text-warn')}>{value}</span>
    </li>
  )
}
