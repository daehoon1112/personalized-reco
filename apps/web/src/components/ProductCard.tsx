import { useImpression } from '../useImpression'
import type { Item } from '../types'

const CATEGORY_EMOJI: Record<string, string> = {
  fashion: '👕',
  beauty: '💄',
  food: '🥐',
  living: '🛋️',
  digital: '🎧',
  sports: '🏃',
  kids: '🧸',
  pet: '🐾',
}

export const displayName = (item: Item): string =>
  item.name ?? `${item.brand ?? '노브랜드'} ${item.category ?? ''} ${item.itemId.slice(-4)}`.trim()

export const formatPrice = (price: number | null): string =>
  price == null ? '가격 미정' : `${price.toLocaleString('ko-KR')}원`

interface Props {
  item: Item
  position: number
  impressionKey: string // requestId — 같은 노출 배치에서 1회만 기록
  onImpression: () => void
  onClick: () => void
}

export function ProductCard({ item, position, impressionKey, onImpression, onClick }: Props) {
  const ref = useImpression(onImpression, impressionKey)

  return (
    <div ref={ref} className="card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}>
      <div className={`thumb cat-${item.category ?? 'etc'}`}>
        <span className="emoji">{CATEGORY_EMOJI[item.category ?? ''] ?? '📦'}</span>
        <span className="pos-badge">#{position}</span>
      </div>
      <div className="card-body">
        <div className="brand">{item.brand ?? ''}</div>
        <div className="name">{displayName(item)}</div>
        <div className="price">{formatPrice(item.price)}</div>
      </div>
    </div>
  )
}
