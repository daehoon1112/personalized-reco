package me.imweb.reco.serving.domain

import java.math.BigDecimal
import java.time.Instant

/**
 * 골드 유저×아이템 상호작용 (`user_item_interaction`, V4). CF(implicit/LightFM) 희소행렬 입력.
 * 유니크 = (userId, itemId) (ux_useriteminteraction_userid_itemid).
 */
data class UserItemInteraction(
    val id: Long? = null,
    val userId: String,
    val itemId: String,
    val impressionCount: Int = 0,
    val clickCount: Int = 0,
    val cartCount: Int = 0,
    val purchaseCount: Int = 0,
    val weight: BigDecimal,          // 암묵 피드백 가중합 (EVENT_WEIGHTS, 파이프라인과 동일 규칙)
    val lastEventDate: Instant,
    val createDate: Instant? = null,
    val updateDate: Instant? = null,
)
