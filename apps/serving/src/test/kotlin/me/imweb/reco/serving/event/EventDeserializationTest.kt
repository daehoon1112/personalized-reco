package me.imweb.reco.serving.event

import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import me.imweb.reco.event.Event
import me.imweb.reco.event.EventType
import tools.jackson.module.kotlin.jacksonObjectMapper
import tools.jackson.module.kotlin.readValue
import java.time.Instant

/**
 * 계약 테스트 — 컨슈머가 Kafka/bronze payload(JSON)를 [Event]로 역직렬화할 수 있는지.
 * 픽스처는 data/samples/events.sample.jsonl 실제 라인과 동일한 형태를 쓴다.
 */
class EventDeserializationTest :
    StringSpec({
        val mapper = jacksonObjectMapper()

        "impression 이벤트를 타입드 Event로 역직렬화한다" {
            val json =
                """
                {"eventId": "8c932752-7ddf-4be3-87d9-23d443f6a23c", "eventType": "impression",
                 "userId": "u-000116", "itemId": "p-0120",
                 "sessionId": "5bbf563c-1555-4083-befb-11c44edeee63", "position": 1, "consent": true,
                 "ts": "2026-06-27T00:15:00.000Z",
                 "context": {"device": "pc", "page": "category",
                             "requestId": "3729ac5a-41c0-4c60-ac07-2a9a065869e1", "modelVersion": "pop-v0"}}
                """.trimIndent()

            val event = mapper.readValue<Event>(json)

            event.eventType shouldBe EventType.IMPRESSION
            event.isImpression shouldBe true
            event.userId shouldBe "u-000116"
            event.position shouldBe 1
            event.ts shouldBe Instant.parse("2026-06-27T00:15:00.000Z")
            event.context.shouldNotBeNull().requestId shouldBe "3729ac5a-41c0-4c60-ac07-2a9a065869e1"
            event.attributionKey shouldBe
                Triple(
                    "5bbf563c-1555-4083-befb-11c44edeee63",
                    "3729ac5a-41c0-4c60-ac07-2a9a065869e1",
                    "p-0120",
                )
        }

        "purchase 이벤트는 주문 컨텍스트(orderId/amount)까지 역직렬화한다" {
            val json =
                """
                {"eventId": "e-1", "eventType": "purchase", "userId": "u-1", "itemId": "p-1",
                 "sessionId": "s-1", "position": null, "consent": true, "ts": "2026-06-27T01:00:00Z",
                 "context": {"device": "mobile", "page": "home", "requestId": "r-1", "modelVersion": "pop-v0",
                             "orderId": "o-abc", "quantity": 2, "unitPrice": 12900, "amount": 25800, "currency": "KRW"}}
                """.trimIndent()

            val event = mapper.readValue<Event>(json)

            event.eventType shouldBe EventType.PURCHASE
            val ctx = event.context.shouldNotBeNull()
            ctx.orderId shouldBe "o-abc"
            ctx.quantity shouldBe 2
            ctx.amount shouldBe 25_800L
            ctx.currency shouldBe "KRW"
        }

        "모르는 필드가 추가돼도 역직렬화는 깨지지 않는다 (전방 호환)" {
            val json =
                """
                {"eventId": "e-2", "eventType": "click", "itemId": "p-2", "ts": "2026-06-27T02:00:00Z",
                 "futureField": "x", "context": {"device": "pc", "newContextKey": 123}}
                """.trimIndent()

            val event = mapper.readValue<Event>(json)

            event.eventType shouldBe EventType.CLICK
            event.userId shouldBe null
            event.context.shouldNotBeNull().device shouldBe "pc"
        }

        "알 수 없는 eventType은 실패한다 (조용히 통과 금지)" {
            val json = """{"eventId": "e-3", "eventType": "wishlist", "ts": "2026-06-27T03:00:00Z"}"""

            runCatching { mapper.readValue<Event>(json) }.isFailure shouldBe true
        }
    })
