import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchItems, fetchRecommendations, fetchUsers } from './api'
import { loadIdentity, setConsent, switchUser } from './identity'
import { buildEnvelope, Tracker, wireUnloadFlush } from './tracker'
import { ProductCard } from './components/ProductCard'
import { ProductModal } from './components/ProductModal'
import type { ExposureContext, TrackerIdentity } from './tracker'
import type { Item, RecommendationsResponse } from './types'

const tracker = new Tracker()
wireUnloadFlush(tracker)

interface Selected {
  item: Item
  position: number
  exposure: ExposureContext
}

interface Exposed<T> {
  data: T
  exposure: ExposureContext
}

export default function App() {
  const [identity, setIdentity] = useState<TrackerIdentity>(() => loadIdentity('anonymous'))
  const [userIds, setUserIds] = useState<string[]>([])
  const [grid, setGrid] = useState<Exposed<Item[]> | null>(null)
  const [rail, setRail] = useState<Exposed<RecommendationsResponse> | null>(null)
  const [selected, setSelected] = useState<Selected | null>(null)
  const [sentCount, setSentCount] = useState(0)

  // 유저 목록 (스위처) — 최초 1회
  useEffect(() => {
    fetchUsers()
      .then(({ userIds }) => {
        setUserIds(userIds)
        // 저장된 유저가 없으면 첫 시드 유저로
        if (loadIdentity('').userId === '' && userIds.length > 0) {
          setIdentity(switchUser(userIds[0]))
        }
      })
      .catch(() => setUserIds([]))
  }, [])

  // 상품 그리드 — 노출 배치(requestId)는 fetch 1회당 하나
  useEffect(() => {
    fetchItems(60)
      .then(({ items }) =>
        setGrid({
          data: items,
          exposure: { requestId: crypto.randomUUID(), page: 'home', modelVersion: 'catalog-v0' },
        }),
      )
      .catch(() => setGrid(null))
  }, [])

  // 추천 레일 — 유저가 바뀌면 다시 요청 (새 노출 배치)
  useEffect(() => {
    fetchRecommendations(identity.userId)
      .then((data) =>
        setRail({
          data,
          exposure: { requestId: crypto.randomUUID(), page: 'home', modelVersion: data.strategy },
        }),
      )
      .catch(() => setRail(null))
  }, [identity.userId])

  const byItemId = useMemo(
    () => new Map((grid?.data ?? []).map((item) => [item.itemId, item])),
    [grid],
  )

  const logImpression = useCallback(
    (itemId: string, position: number, exposure: ExposureContext) => {
      tracker.impression(buildEnvelope('impression', identity, itemId, position, exposure))
      setSentCount((n) => n + 1)
    },
    [identity],
  )

  const open = (item: Item, position: number, exposure: ExposureContext) => {
    tracker.action(buildEnvelope('click', identity, item.itemId, position, exposure))
    setSentCount((n) => n + 1)
    setSelected({ item, position, exposure })
  }

  const commerce = (type: 'cart' | 'purchase', quantity: number) => {
    if (!selected) return
    tracker.action(
      buildEnvelope(type, identity, selected.item.itemId, selected.position, selected.exposure, {
        quantity,
        unitPrice: selected.item.price ?? 0,
        currency: selected.item.currency,
      }),
    )
    setSentCount((n) => n + 1)
  }

  return (
    <div className="app">
      <header>
        <h1>reco 데모 스토어</h1>
        <div className="controls">
          <label>
            유저
            <select
              value={identity.userId}
              onChange={(e) => setIdentity(switchUser(e.target.value))}
            >
              {!userIds.includes(identity.userId) && (
                <option value={identity.userId}>{identity.userId}</option>
              )}
              {userIds.map((id) => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </label>
          <label className="consent">
            <input
              type="checkbox"
              checked={identity.consent}
              onChange={(e) => setIdentity(setConsent(identity, e.target.checked))}
            />
            추적 동의
          </label>
          <span className="counter" title="이 세션에서 만든 이벤트 수">
            📨 {sentCount}
          </span>
        </div>
      </header>

      <section className="rail">
        <h2>
          {identity.userId}님을 위한 추천
          {rail && <small> · {rail.data.strategy}</small>}
        </h2>
        {rail === null ? (
          <p className="empty">추천을 불러오지 못했습니다 — serving(:8080)이 떠 있는지 확인</p>
        ) : (
          <div className="rail-track">
            {rail.data.items.map((rec, idx) => {
              const item: Item = byItemId.get(rec.itemId) ?? {
                itemId: rec.itemId, name: null, category: null, brand: null,
                price: null, currency: 'KRW',
              }
              const position = idx + 1
              return (
                <ProductCard
                  key={`${rail.exposure.requestId}-${rec.itemId}`}
                  item={item}
                  position={position}
                  impressionKey={rail.exposure.requestId}
                  onImpression={() => logImpression(rec.itemId, position, rail.exposure)}
                  onClick={() => open(item, position, rail.exposure)}
                />
              )
            })}
          </div>
        )}
      </section>

      <section>
        <h2>전체 상품</h2>
        {grid === null ? (
          <p className="empty">상품을 불러오지 못했습니다</p>
        ) : (
          <div className="grid">
            {grid.data.map((item, idx) => {
              const position = idx + 1
              return (
                <ProductCard
                  key={`${grid.exposure.requestId}-${item.itemId}`}
                  item={item}
                  position={position}
                  impressionKey={grid.exposure.requestId}
                  onImpression={() => logImpression(item.itemId, position, grid.exposure)}
                  onClick={() => open(item, position, grid.exposure)}
                />
              )
            })}
          </div>
        )}
      </section>

      {selected && (
        <ProductModal
          item={selected.item}
          onCart={(qty) => commerce('cart', qty)}
          onPurchase={(qty) => commerce('purchase', qty)}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
