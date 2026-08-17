package me.imweb.reco.event

import com.fasterxml.jackson.annotation.JsonValue

/**
 * 행동 이벤트 타입. 와이어 포맷(JSON)은 소문자 문자열 — recommender(EVENT_WEIGHTS)와 동일 코드.
 */
enum class EventType(
    @get:JsonValue val code: String,
) {
    IMPRESSION("impression"),
    CLICK("click"),
    CART("cart"),
    PURCHASE("purchase"),
    ;

    companion object {
        fun from(code: String): EventType =
            entries.firstOrNull { it.code == code }
                ?: throw IllegalArgumentException("알 수 없는 eventType: $code")
    }
}
