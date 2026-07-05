package me.imweb.reco.event

/**
 * 이벤트 컨텍스트 (typed view).
 *
 * impression 시점 스냅샷 + 행동별 부가 정보. 전 필드 optional —
 * 이벤트 타입에 따라 채워지는 필드가 다르다(quantity=cart/purchase, orderId 이하=purchase).
 * Jackson 3는 기본으로 unknown 필드를 무시하므로 컨텍스트가 확장돼도 역직렬화는 깨지지 않는다.
 */
data class EventContext(
    val device: String? = null,
    val page: String? = null,
    val requestId: String? = null,     // 노출 배치 키 — silver 라벨링의 impression↔결과 조인 키
    val modelVersion: String? = null,  // 노출을 만든 서빙 모델 버전
    val quantity: Int? = null,
    val orderId: String? = null,
    val unitPrice: Long? = null,       // KRW 정수
    val amount: Long? = null,          // KRW 정수 (unitPrice × quantity)
    val currency: String? = null,
)
