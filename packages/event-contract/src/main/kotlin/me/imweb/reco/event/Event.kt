package me.imweb.reco.event

import java.time.Instant

/**
 * 소비(consume) 측 타입드 이벤트 — Kafka `events` 토픽 / bronze `events_raw.payload` 역직렬화용.
 *
 * 수집(ingest) 경로는 serving의 `EventEnvelope`를 쓴다: bronze는 "받은 그대로"를 보존해야 해서
 * context를 Map으로 pass-through 한다. 이 클래스는 그 반대편 — 소비/가공 단계에서
 * 검증된 형태로 읽을 때 사용한다(eventId/ts는 수집 시 서버가 채우므로 여기선 non-null).
 */
data class Event(
    val eventId: String,
    val eventType: EventType,
    val userId: String? = null,      // 비회원 NULL
    val itemId: String? = null,
    val sessionId: String? = null,
    val position: Int? = null,       // impression/click만, 1-base
    val consent: Boolean? = null,
    val ts: Instant,
    val context: EventContext? = null,
) {
    val isImpression: Boolean get() = eventType == EventType.IMPRESSION

    /** silver 라벨링에서 결과(click/cart/purchase)를 impression에 귀속할 때 쓰는 조인 키. */
    val attributionKey: Triple<String?, String?, String?>
        get() = Triple(sessionId, context?.requestId, itemId)
}
