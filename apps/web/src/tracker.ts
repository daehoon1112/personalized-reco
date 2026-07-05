/** 행동 이벤트 트래커 — 엔벨로프 조립 + 배치 전송(POST /events).
 *
 * 설계:
 * - impression은 큐에 모아 FLUSH_MS/FLUSH_MAX 기준으로 배치 전송 (fire-and-forget, 202).
 * - click/cart/purchase는 즉시 전송 (사용자 행동은 유실 비용이 크다).
 * - 탭 이탈(visibilitychange hidden) 시 잔여 큐를 sendBeacon으로 밀어낸다.
 * - requestId: 노출 배치(추천 응답/그리드 렌더 1회)의 키. 같은 노출에서 이어진
 *   click/cart/purchase가 공유한다 → silver 라벨링의 impression↔결과 조인 키.
 * - consent=false면 이벤트를 만들되 개인 식별(userId)을 익명으로 바꾸지 않고 플래그만 실어 보낸다
 *   (다운스트림에서 처리 — 스키마 계약대로 consent 필드가 진실).
 */

import type { EventEnvelope, EventType } from './types'

const FLUSH_MS = 800
const FLUSH_MAX = 50

export interface TrackerIdentity {
  userId: string
  sessionId: string
  consent: boolean
}

export interface ExposureContext {
  requestId: string
  page: string
  modelVersion: string
}

export interface CommerceDetail {
  quantity: number
  unitPrice: number
  currency: string
  orderId?: string
}

const device = (): string =>
  typeof navigator !== 'undefined' && /Mobi|Android|iPhone/i.test(navigator.userAgent)
    ? 'mobile'
    : 'pc'

export function buildEnvelope(
  type: EventType,
  identity: TrackerIdentity,
  itemId: string,
  position: number | null,
  exposure: ExposureContext,
  detail?: CommerceDetail,
): EventEnvelope {
  const envelope: EventEnvelope = {
    eventId: crypto.randomUUID(),
    eventType: type,
    userId: identity.userId,
    itemId,
    sessionId: identity.sessionId,
    // 계약: position은 impression/click에만 (cart/purchase는 null — position bias 보정용)
    position: type === 'impression' || type === 'click' ? position : null,
    consent: identity.consent,
    ts: new Date().toISOString(),
    context: {
      device: device(),
      page: exposure.page,
      requestId: exposure.requestId,
      modelVersion: exposure.modelVersion,
    },
  }
  if (detail && (type === 'cart' || type === 'purchase')) {
    envelope.context.quantity = detail.quantity
    if (type === 'purchase') {
      envelope.context.orderId = detail.orderId ?? `o-${crypto.randomUUID().slice(0, 8)}`
      envelope.context.unitPrice = detail.unitPrice
      envelope.context.amount = detail.unitPrice * detail.quantity
      envelope.context.currency = detail.currency
    }
  }
  return envelope
}

type Sender = (events: EventEnvelope[]) => void

const defaultSender: Sender = (events) => {
  // keepalive: 페이지 전환 중에도 전송 완료 (fire-and-forget — 202 응답은 신뢰하고 버린다)
  void fetch('/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(events),
    keepalive: true,
  }).catch(() => {
    /* 데모 트래커 — 전송 실패는 조용히 버린다 (서버가 내려간 경우 등) */
  })
}

export class Tracker {
  private queue: EventEnvelope[] = []
  private timer: ReturnType<typeof setTimeout> | null = null

  constructor(private readonly send: Sender = defaultSender) {}

  /** impression — 큐잉 후 배치 전송. */
  impression(envelope: EventEnvelope): void {
    this.queue.push(envelope)
    if (this.queue.length >= FLUSH_MAX) {
      this.flush()
      return
    }
    this.timer ??= setTimeout(() => this.flush(), FLUSH_MS)
  }

  /** click/cart/purchase — 즉시 전송 (잔여 impression도 같이 밀어 순서 보존). */
  action(envelope: EventEnvelope): void {
    this.queue.push(envelope)
    this.flush()
  }

  flush(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    if (this.queue.length === 0) return
    const batch = this.queue
    this.queue = []
    this.send(batch)
  }

  get pending(): number {
    return this.queue.length
  }
}

/** 탭 이탈 시 잔여 큐를 sendBeacon으로 배출 — 브라우저 환경에서만 배선. */
export function wireUnloadFlush(tracker: Tracker): void {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') tracker.flush()
  })
}
