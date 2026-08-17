package me.imweb.reco.serving.api

import me.imweb.reco.serving.catalog.CatalogReader
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/**
 * 카탈로그 메타 API — 스토어프론트(apps/web) 전용 읽기 엔드포인트.
 *
 * 추천이 아니라 마스터 데이터 조회다(추천은 /api/recommendations, #8).
 */
@RestController
class CatalogController(
    private val reader: CatalogReader,
) {
    data class ItemResponse(
        val itemId: String,
        val name: String?,
        val category: String?,
        val brand: String?,
        val price: Long?,
        val currency: String,
    )

    data class ItemsResponse(
        val items: List<ItemResponse>,
    )

    data class UsersResponse(
        val userIds: List<String>,
    )

    @GetMapping("/api/items")
    fun items(
        @RequestParam(defaultValue = "60") limit: Int,
    ): ItemsResponse =
        ItemsResponse(
            reader.listSellableItems(limit.coerceIn(1, MAX_LIMIT)).map {
                ItemResponse(
                    itemId = it.itemId,
                    name = it.name,
                    category = it.category,
                    brand = it.brand,
                    price = it.price,
                    currency = it.currency,
                )
            },
        )

    @GetMapping("/api/users")
    fun users(
        @RequestParam(defaultValue = "24") limit: Int,
    ): UsersResponse = UsersResponse(reader.listUserIds(limit.coerceIn(1, MAX_LIMIT)))

    companion object {
        private const val MAX_LIMIT = 300
    }
}
