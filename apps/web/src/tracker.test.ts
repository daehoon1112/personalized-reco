/** 트래커 단위 테스트 — 엔벨로프 계약 + 배치/즉시 전송 동작 (네트워크 없음, sender 주입). */

import { describe, expect, it, vi } from 'vitest'
import { buildEnvelope, Tracker } from './tracker'
import type { TrackerIdentity } from './tracker'
import type { EventEnvelope } from './types'

const identity: TrackerIdentity = {
  userId: 'u-000001',
  sessionId: 'sess-1',
  consent: true,
}

const exposure = { requestId: 'req-1', page: 'home', modelVersion: 'catalog-v0' }

describe('buildEnvelope — 이벤트 계약 (Kotlin EventEnvelope · py_common 거울상)', () => {
  it('impression/click은 position을 싣고, cart/purchase는 null', () => {
    expect(buildEnvelope('impression', identity, 'p-0001', 3, exposure).position).toBe(3)
    expect(buildEnvelope('click', identity, 'p-0001', 3, exposure).position).toBe(3)
    const cart = buildEnvelope('cart', identity, 'p-0001', 3, exposure, {
      quantity: 1, unitPrice: 1000, currency: 'KRW',
    })
    expect(cart.position).toBeNull()
  })

  it('같은 노출의 이벤트는 requestId를 공유한다 (silver 조인 키)', () => {
    const imp = buildEnvelope('impression', identity, 'p-0001', 1, exposure)
    const click = buildEnvelope('click', identity, 'p-0001', 1, exposure)
    expect(imp.context.requestId).toBe(click.context.requestId)
  })

  it('purchase는 orderId·amount(단가×수량)·currency를 완비한다', () => {
    const purchase = buildEnvelope('purchase', identity, 'p-0001', 1, exposure, {
      quantity: 3, unitPrice: 10_000, currency: 'KRW',
    })
    expect(purchase.context.orderId).toMatch(/^o-/)
    expect(purchase.context.amount).toBe(30_000)
    expect(purchase.context.unitPrice).toBe(10_000)
    expect(purchase.context.currency).toBe('KRW')
  })

  it('cart는 quantity만 싣는다 (orderId/amount 없음)', () => {
    const cart = buildEnvelope('cart', identity, 'p-0001', 1, exposure, {
      quantity: 2, unitPrice: 10_000, currency: 'KRW',
    })
    expect(cart.context.quantity).toBe(2)
    expect(cart.context.orderId).toBeUndefined()
    expect(cart.context.amount).toBeUndefined()
  })

  it('consent 플래그가 그대로 실린다', () => {
    const noConsent = buildEnvelope('impression', { ...identity, consent: false }, 'p-1', 1, exposure)
    expect(noConsent.consent).toBe(false)
  })
})

describe('Tracker — 배치/즉시 전송', () => {
  const impression = () => buildEnvelope('impression', identity, 'p-0001', 1, exposure)

  it('impression은 큐잉되고 타이머 후 배치로 나간다', () => {
    vi.useFakeTimers()
    const send = vi.fn<(events: EventEnvelope[]) => void>()
    const tracker = new Tracker(send)

    tracker.impression(impression())
    tracker.impression(impression())
    expect(send).not.toHaveBeenCalled()
    expect(tracker.pending).toBe(2)

    vi.runAllTimers()
    expect(send).toHaveBeenCalledTimes(1)
    expect(send.mock.calls[0][0]).toHaveLength(2)
    expect(tracker.pending).toBe(0)
    vi.useRealTimers()
  })

  it('50건 차면 타이머를 기다리지 않고 즉시 배출한다', () => {
    const send = vi.fn<(events: EventEnvelope[]) => void>()
    const tracker = new Tracker(send)
    for (let i = 0; i < 50; i++) tracker.impression(impression())
    expect(send).toHaveBeenCalledTimes(1)
    expect(send.mock.calls[0][0]).toHaveLength(50)
  })

  it('action(click 등)은 잔여 impression과 함께 즉시 나간다 (순서 보존)', () => {
    const send = vi.fn<(events: EventEnvelope[]) => void>()
    const tracker = new Tracker(send)

    tracker.impression(impression())
    tracker.action(buildEnvelope('click', identity, 'p-0001', 1, exposure))

    expect(send).toHaveBeenCalledTimes(1)
    const batch = send.mock.calls[0][0]
    expect(batch.map((e) => e.eventType)).toEqual(['impression', 'click'])
  })
})
