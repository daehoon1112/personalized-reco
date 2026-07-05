package me.imweb.reco.serving.domain

import java.time.Instant

/**
 * 실버 라벨링된 노출 (`impression_label`, V3). 1 impression = 1행.
 * 비즈니스 키 = [impressionId] = bronze `events_raw.event_id` 논리 참조 (ux_impressionlabel_impressionid).
 *
 * [label]은 플래그에서 유도된다(최대 행동). attribution 규칙은 [labelVersion]에 기록 —
 * 서로 다른 버전을 섞어 학습하지 말 것 (docs/data-model.md).
 */
data class ImpressionLabel(
    val id: Long? = null,
    val impressionId: String,
    val eventDate: Instant,
    val userId: String? = null,
    val itemId: String,
    val sessionId: String? = null,
    val requestId: String? = null,
    val position: Int? = null,
    val device: String? = null,        // 이하 impression 시점 스냅샷 (point-in-time)
    val page: String? = null,
    val modelVersion: String? = null,
    val isClick: Boolean = false,
    val clickDate: Instant? = null,
    val isCart: Boolean = false,
    val cartDate: Instant? = null,
    val isPurchase: Boolean = false,
    val purchaseDate: Instant? = null,
    val purchaseAmount: Long? = null,  // KRW 정수
    val labelVersion: String,
    val createDate: Instant? = null,
) {
    /** 최대 행동 라벨: 0=none, 1=click, 2=cart, 3=purchase. */
    val label: Int
        get() = when {
            isPurchase -> LABEL_PURCHASE
            isCart -> LABEL_CART
            isClick -> LABEL_CLICK
            else -> LABEL_NONE
        }

    init {
        // 퍼널 정합성: 상위 행동은 하위 행동을 전제한다 (라벨링 배치 버그 조기 검출)
        require(!isPurchase || isCart || isClick) { "purchase는 click/cart 없이 존재할 수 없음: $impressionId" }
        require(!isCart || isClick) { "cart는 click 없이 존재할 수 없음: $impressionId" }
    }

    companion object {
        const val LABEL_NONE = 0
        const val LABEL_CLICK = 1
        const val LABEL_CART = 2
        const val LABEL_PURCHASE = 3
    }
}
