package me.imweb.reco.serving.api

import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import me.imweb.reco.serving.catalog.CatalogReader
import me.imweb.reco.serving.domain.Item

/** 단위 테스트 — CatalogReader는 MockK mock, 매핑·limit 클램프만 검증. */
class CatalogControllerTest : StringSpec({

    val reader = mockk<CatalogReader>()
    val controller = CatalogController(reader)

    "items 는 판매 아이템을 DTO로 매핑한다" {
        every { reader.listSellableItems(any()) } returns listOf(
            Item(itemId = "p-0001", category = "food", brand = "daily-object", price = 117_800),
        )

        val response = controller.items(limit = 60)

        response.items.size shouldBe 1
        with(response.items.first()) {
            itemId shouldBe "p-0001"
            category shouldBe "food"
            brand shouldBe "daily-object"
            price shouldBe 117_800L
            currency shouldBe "KRW"
        }
    }

    "limit 은 1~300으로 클램프된다" {
        every { reader.listSellableItems(any()) } returns emptyList()

        controller.items(limit = 9999)
        verify { reader.listSellableItems(300) }

        controller.items(limit = -5)
        verify { reader.listSellableItems(1) }
    }

    "users 는 user_id 목록을 반환한다" {
        every { reader.listUserIds(24) } returns listOf("u-000001", "u-000002")

        controller.users(limit = 24).userIds shouldBe listOf("u-000001", "u-000002")
    }
})
