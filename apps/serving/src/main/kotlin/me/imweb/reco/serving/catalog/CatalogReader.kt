package me.imweb.reco.serving.catalog

import me.imweb.reco.serving.domain.Item
import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.stereotype.Repository

/**
 * 카탈로그 조회 (item/user_profile 마스터). 스토어프론트(apps/web)의 상품 그리드·유저 스위처 소스.
 */
@Repository
class CatalogReader(
    private val jdbc: JdbcClient,
) {
    /** 판매 중(sale, 미삭제) 아이템 — id 순(=시드 순서, zipf 인기 상위가 앞에 온다). */
    fun listSellableItems(limit: Int): List<Item> =
        jdbc
            .sql(
                """
                SELECT item_id, name, category, brand, price, currency, status_cd
                FROM item
                WHERE is_delete = false AND status_cd = :status
                ORDER BY id
                LIMIT :limit
                """.trimIndent(),
            ).param("status", Item.STATUS_SALE)
            .param("limit", limit)
            .query { rs, _ ->
                Item(
                    itemId = rs.getString("item_id"),
                    name = rs.getString("name"),
                    category = rs.getString("category"),
                    brand = rs.getString("brand"),
                    price = rs.getLong("price").let { if (rs.wasNull()) null else it },
                    currency = rs.getString("currency"),
                    statusCd = rs.getString("status_cd"),
                )
            }.list()

    /** 데모 유저 스위처용 user_id 목록. */
    fun listUserIds(limit: Int): List<String> =
        jdbc
            .sql(
                """
                SELECT user_id FROM user_profile
                WHERE is_delete = false
                ORDER BY id
                LIMIT :limit
                """.trimIndent(),
            ).param("limit", limit)
            .query { rs, _ -> rs.getString("user_id") }
            .list()
}
