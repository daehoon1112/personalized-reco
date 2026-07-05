/** serving API 응답 타입 — Kotlin DTO의 거울상. */

export interface Item {
  itemId: string
  name: string | null
  category: string | null
  brand: string | null
  price: number | null
  currency: string
}

export interface RecommendedItem {
  itemId: string
  score: number
}

export interface RecommendationsResponse {
  userId: string
  strategy: string
  items: RecommendedItem[]
}

export type EventType = 'impression' | 'click' | 'cart' | 'purchase'

/** 이벤트 엔벨로프 (camelCase 와이어 포맷 — Kotlin EventEnvelope · py_common.event 계약과 동일). */
export interface EventEnvelope {
  eventId: string
  eventType: EventType
  userId: string
  itemId: string
  sessionId: string
  position: number | null
  consent: boolean
  ts: string
  context: {
    device: string
    page: string
    requestId: string
    modelVersion: string
    quantity?: number
    orderId?: string
    unitPrice?: number
    amount?: number
    currency?: string
  }
}
