package me.imweb.reco.serving.domain

import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate

/**
 * 골드 인기순 집계 (`item_popularity`, V4). 인기순 배치(#10)가 적재, 콜드스타트 폴백의 원천.
 * 유니크 = (baseDate, windowDays, itemId) (ux_itempopularity_basedate_windowdays_itemid).
 */
data class ItemPopularity(
    val id: Long? = null,
    val baseDate: LocalDate,
    val windowDays: Int,             // 7 | 30
    val itemId: String,
    val impressionCount: Long = 0,
    val clickCount: Long = 0,
    val cartCount: Long = 0,
    val purchaseCount: Long = 0,
    val buyerCount: Long = 0,        // 중복 제거 구매자 수
    val score: BigDecimal,           // 행동 가중합 + 시간 감쇠
    val createDate: Instant? = null,
) {
    val clickThroughRate: Double
        get() = if (impressionCount > 0) clickCount.toDouble() / impressionCount else 0.0
}
