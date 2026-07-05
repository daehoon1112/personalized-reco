package me.imweb.reco.serving.domain

import java.time.Instant

/**
 * 아이템 마스터 (`item`, V2). 비즈니스 키 = [itemId] (ux_item_itemid).
 */
data class Item(
    val id: Long? = null,            // 미저장 상태면 null (PK는 DB가 채번)
    val itemId: String,
    val name: String? = null,
    val category: String? = null,
    val brand: String? = null,
    val price: Long? = null,         // KRW 정수
    val currency: String = "KRW",
    val statusCd: String = STATUS_SALE,
    val description: String? = null,
    val attrs: Map<String, Any?> = emptyMap(),  // jsonb 확장 슬롯 (임베딩 소스, 이미지 URL 등)
    val isDelete: Boolean = false,
    val createDate: Instant? = null,
    val updateDate: Instant? = null,
    val deleteDate: Instant? = null,
) {
    val isSellable: Boolean get() = !isDelete && statusCd == STATUS_SALE

    companion object {
        const val STATUS_SALE = "sale"
        const val STATUS_SOLDOUT = "soldout"
        const val STATUS_HIDDEN = "hidden"
    }
}
