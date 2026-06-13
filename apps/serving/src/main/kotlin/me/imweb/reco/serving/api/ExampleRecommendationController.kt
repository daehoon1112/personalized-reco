package me.imweb.reco.serving.api

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/**
 * 예시 추천 API (스캐폴딩).
 *
 * 실제 사전계산 결과 조회 + 콜드스타트 폴백 + 비동기 impression 로깅은 #8에서 구현한다.
 * 지금은 동작 확인용으로 고정된 인기순 예시를 반환한다.
 */
@RestController
class ExampleRecommendationController {

    data class RecommendedItem(val itemId: String, val score: Double)

    data class RecommendationsResponse(
        val userId: String,
        val strategy: String,
        val items: List<RecommendedItem>,
    )

    @GetMapping("/api/recommendations")
    fun recommend(
        @RequestParam(defaultValue = "anonymous") userId: String,
    ): RecommendationsResponse =
        RecommendationsResponse(
            userId = userId,
            strategy = "popularity-fallback (example)",
            items = listOf(
                RecommendedItem("item-1", 0.92),
                RecommendedItem("item-2", 0.81),
                RecommendedItem("item-3", 0.77),
            ),
        )
}
