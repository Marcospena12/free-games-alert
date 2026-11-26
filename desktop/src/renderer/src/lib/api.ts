import type {
  AboutInfo,
  Group,
  MonitorError,
  Post,
  Settings,
  Snapshot,
  StoreInfo,
} from './types'

/**
 * Cliente da API local. A base (porta + token) vem do processo principal
 * via preload (`window.fgh`).
 */
let baseInfo: { baseUrl: string; token: string } | null = null

export async function initApi(): Promise<void> {
  const info = await window.fgh.getBackendInfo()
  if (!info) throw new Error('serviço interno indisponível')
  baseInfo = { baseUrl: `http://127.0.0.1:${info.port}`, token: info.token }
}

function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!baseInfo) throw new Error('API não inicializada')
  const headers: Record<string, string> = {
    ...(baseInfo.token ? { 'X-FGH-Token': baseInfo.token } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (init?.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  return fetch(`${baseInfo.baseUrl}${path}`, { ...init, headers }).then(async (res) => {
    if (!res.ok) {
      const body = await res.json().catch(() => null)
      throw new Error((body as { detail?: string } | null)?.detail ?? `HTTP ${res.status}`)
    }
    return res.json() as Promise<T>
  })
}

function post<T>(path: string, body: unknown = {}): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  snapshot: () => request<Snapshot>('/api/snapshot'),
  about: () => request<AboutInfo>('/api/about'),
  posts: (
    params: {
      limit?: number
      status?: string
      store?: string
      search?: string
      library?: boolean
      active?: boolean
    } = {},
  ) => {
    const qs = new URLSearchParams()
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.status) qs.set('status', params.status)
    if (params.store) qs.set('store', params.store)
    if (params.search) qs.set('search', params.search)
    if (params.library !== undefined) qs.set('library', String(params.library))
    if (params.active !== undefined) qs.set('active', String(params.active))
    const query = qs.toString()
    return request<Post[]>(`/api/posts${query ? `?${query}` : ''}`)
  },
  groups: () => request<Group[]>('/api/groups'),
  createGroup: (payload: { name: string; url: string; active?: boolean }) =>
    post<Group>('/api/groups', payload),
  updateGroup: (id: number, payload: { name: string; url: string; active: boolean }) =>
    request<Group>(`/api/groups/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteGroup: (id: number) =>
    request<{ ok: boolean }>(`/api/groups/${id}`, { method: 'DELETE' }),
  errors: (limit = 50) => request<MonitorError[]>(`/api/errors?limit=${limit}`),
  stores: () => request<StoreInfo[]>('/api/stores'),
  settings: () => request<Settings>('/api/settings'),
  updateSettings: (payload: Partial<Settings>) =>
    request<Settings>('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  check: (forcePrices = false) => post<{ ok: boolean; started: boolean }>('/api/check', {
    force_prices: forcePrices,
  }),
  testNotification: () => post<{ ok: boolean }>('/api/notifications/test'),
  setInLibrary: (id: number, inLibrary: boolean) =>
    request<Post>(`/api/posts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ in_library: inLibrary }),
    }),
}
