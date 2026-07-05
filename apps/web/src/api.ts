/** serving API 클라이언트 — dev 프록시(/api, /events → :8080) 경유. */

import type { Item, RecommendationsResponse } from './types'

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`${url} → ${resp.status}`)
  return (await resp.json()) as T
}

export const fetchItems = (limit = 60): Promise<{ items: Item[] }> =>
  getJson(`/api/items?limit=${limit}`)

export const fetchUsers = (limit = 24): Promise<{ userIds: string[] }> =>
  getJson(`/api/users?limit=${limit}`)

export const fetchRecommendations = (userId: string): Promise<RecommendationsResponse> =>
  getJson(`/api/recommendations?userId=${encodeURIComponent(userId)}`)
