package me.imweb.reco.serving.domain

import java.math.BigDecimal
import java.time.Instant

/**
 * 배치 사전계산 추천 결과 (`recommendation`, V4). 추천 API(#8)가 읽는 서빙 테이블.
 * 유니크 = (userId, rank) (ux_recommendation_userid_rank).
 */
data class Recommendation(
    val id: Long? = null,
    val userId: String,              // 콜드스타트 전역 폴백 행은 [GLOBAL_USER]
    val rank: Int,                   // 1-base
    val itemId: String,
    val score: BigDecimal,
    val strategy: String,            // popularity | cf | ...
    val modelVersion: String,
    val computeDate: Instant,
    val createDate: Instant? = null,
) {
    companion object {
        /** 유저별 결과가 없을 때 서빙하는 전역(인기순) 폴백 행의 user_id 센티널. */
        const val GLOBAL_USER = "_global"
    }
}
