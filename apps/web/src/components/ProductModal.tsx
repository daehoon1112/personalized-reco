import { useState } from 'react'
import { displayName, formatPrice } from './ProductCard'
import type { Item } from '../types'

interface Props {
  item: Item
  onCart: (quantity: number) => void
  onPurchase: (quantity: number) => void
  onClose: () => void
}

/** 상품 상세 모달 — 열린 시점에 이미 click 이벤트는 기록된 상태. 여기선 cart/purchase만. */
export function ProductModal({ item, onCart, onPurchase, onClose }: Props) {
  const [quantity, setQuantity] = useState(1)
  const [done, setDone] = useState<'cart' | 'purchase' | null>(null)
  const purchasable = item.price != null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="닫기">×</button>
        <h2>{displayName(item)}</h2>
        <p className="meta">
          {item.brand ?? '브랜드 미상'} · {item.category ?? '기타'} · {item.itemId}
        </p>
        <p className="modal-price">{formatPrice(item.price)}</p>

        <div className="qty">
          수량
          {[1, 2, 3].map((n) => (
            <button key={n} className={quantity === n ? 'qty-btn active' : 'qty-btn'}
              onClick={() => setQuantity(n)}>{n}</button>
          ))}
        </div>

        {done ? (
          <p className="done">
            {done === 'cart' ? '🛒 장바구니에 담았습니다' : '✅ 구매 완료! (purchase 이벤트 전송됨)'}
          </p>
        ) : (
          <div className="actions">
            <button className="btn cart" onClick={() => { onCart(quantity); setDone('cart') }}>
              장바구니 담기
            </button>
            <button className="btn buy" disabled={!purchasable}
              title={purchasable ? '' : '가격 정보가 없어 구매 불가 (스텁 추천 아이템)'}
              onClick={() => { onPurchase(quantity); setDone('purchase') }}>
              바로 구매
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
