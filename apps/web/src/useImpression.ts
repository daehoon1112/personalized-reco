/** 뷰포트 기반 impression 로깅 훅 — 카드가 50% 이상 보일 때 1회만 기록.
 *
 * 렌더 시점이 아니라 실제 노출 시점에 찍는다 — 스크롤 안 한 아래쪽 상품은
 * impression이 없어야 position bias 데이터가 진실이 된다.
 */

import { useEffect, useRef } from 'react'

export function useImpression(onVisible: () => void, key: string): React.RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement | null>(null)
  const fired = useRef<string | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || fired.current === key) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && fired.current !== key) {
            fired.current = key // 같은 노출 배치(requestId) 안에서는 1회만
            onVisible()
            observer.disconnect()
          }
        }
      },
      { threshold: 0.5 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [key, onVisible])

  return ref
}
