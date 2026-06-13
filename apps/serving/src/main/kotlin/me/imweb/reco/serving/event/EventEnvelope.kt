package me.imweb.reco.serving.event

/**
 * 이벤트 엔벨로프 (임시 JSON 계약).
 *
 * TODO(#4): `contracts/proto`에서 생성되는 proto 타입으로 대체한다.
 * 필드는 문서화된 엔벨로프와 정렬: impression/click/cart/purchase 공통.
 */
data class EventEnvelope(
    val eventId: String? = null,
    val eventType: String,
    val userId: String? = null,
    val itemId: String? = null,
    val sessionId: String? = null,
    val position: Int? = null,
    val consent: Boolean? = null,
    val ts: String? = null,
    val context: Map<String, Any?>? = null,
)
