/** Tipos que espelham a serialização da API Python (serialization.py). */

export interface Post {
  id: number
  group_id: number | null
  group_name: string | null
  title: string
  description: string | null
  author: string | null
  publication_url: string | null
  store_url: string | null
  claim_url: string | null
  image_url: string | null
  store: string
  source: string
  store_app_id: number | null
  external_id: string | null
  in_library: boolean
  notified: boolean
  published_at: string | null
  discovered_at: string
  ends_at: string | null
  worth_usd: number | null
  price_status: string | null
  price_initial_cents: number | null
  price_final_cents: number | null
  price_discount_percent: number | null
  price_currency: string | null
  price_source: string | null
  price_checked_at: string | null
  price_error: string | null
}

export interface Group {
  id: number
  name: string
  url: string
  active: boolean
  initialized: boolean
  last_checked_at: string | null
  created_at: string | null
}

export interface MonitorError {
  id: number
  group_id: number | null
  group_name: string | null
  message: string
  created_at: string | null
}

export interface StoreFilterConfig {
  enabled: boolean
  allowed_types: string[]
  min_worth_usd: number | null
  include_na_worth: boolean
  title_include_keywords: string[]
  title_exclude_keywords: string[]
  ignore_no_end_date: boolean
  min_hours_before_expiration: number | null
}

export interface Settings {
  check_interval_minutes: number
  notifications_enabled: boolean
  close_to_tray: boolean
  gamerpower_enabled: boolean
  stores_enabled: string[]
  enabled_types: string[]
  store_filters: Record<string, StoreFilterConfig>
  filter_min_worth_usd: number | null
  filter_include_na_worth: boolean
  filter_ignore_no_end_date: boolean
  filter_exclude_keywords: string[]
}

export interface LastCheck {
  at: number
  new_posts?: number
  errors?: number
  checked_groups?: number
  failed_groups?: number
  failed?: string
}

export interface Snapshot {
  free_now: number
  total_posts: number
  groups: { total: number; active: number }
  last_checked_at: string | null
  settings: Settings
  stores_enabled: string[]
  check_running: boolean
  last_check: LastCheck | null
}

export interface StoreInfo extends StoreFilterConfig {
  id: string
  label: string
}

export interface AboutInfo {
  version: string
  python: string
  platform: string
  data_dir: string
  db_path: string
  db_size_bytes: number
  log_path: string
}

export interface WsEvent {
  type:
    | 'check.started'
    | 'check.finished'
    | 'check.failed'
    | 'posts.updated'
    | 'groups.updated'
    | 'settings.updated'
  data: Record<string, unknown>
}
