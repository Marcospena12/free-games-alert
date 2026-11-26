export type Page = 'dashboard' | 'history' | 'groups' | 'settings'

export const PAGE_TITLES: Record<Page, string> = {
  dashboard: 'Painel',
  history: 'Histórico',
  groups: 'Grupos',
  settings: 'Configurações',
}

const VALID_PAGES = new Set<string>(Object.keys(PAGE_TITLES))

export function pageFromHash(hash: string): Page {
  const value = hash.replace(/^#\/?/, '').trim()
  return VALID_PAGES.has(value) ? (value as Page) : 'dashboard'
}

export function hashForPage(page: Page): string {
  return `#/${page}`
}
