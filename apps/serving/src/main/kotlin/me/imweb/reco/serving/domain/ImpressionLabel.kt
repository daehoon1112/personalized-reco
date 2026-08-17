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
        // purchase는 귀속 anchor(click 또는 cart) 없이 존재할 수 없다 — attribution v1 규칙 그대로.
        require(!isPurchase || isCart || isClick) { "purchase는 click/cart 없이 존재할 수 없음: $impressionId" }
        // cart는 click을 전제하지 않는다. 수집은 fire-and-forget(유실 허용)이라 click만 유실되고
        // cart/purchase가 도착하는 조합이 실제로 관측된다 — 관측된 신호를 버리지 않고 그대로 싣는다.
        // (attribution v1: cart도 impression 기준으로 독립 귀속 — docs/data-model.md)
    }

    companion object {
        const val LABEL_NONE = 0
        const val LABEL_CLICK = 1
        const val LABEL_CART = 2
        const val LABEL_PURCHASE = 3
    }
}
