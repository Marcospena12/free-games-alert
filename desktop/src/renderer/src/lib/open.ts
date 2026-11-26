import type { Post } from './types'
import { postOpenUrl } from './format'

export async function openPost(post: Post): Promise<void> {
  const url = postOpenUrl(post)
  if (!url) throw new Error('Esta oferta não tem link para abrir.')
  await window.fgh.openExternal(url)
}

export async function openUrl(url: string): Promise<void> {
  await window.fgh.openExternal(url)
}
