package me.imweb.reco.bronzesink

import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import me.imweb.reco.event.Event
import me.imweb.reco.event.EventType
import tools.jackson.module.kotlin.jacksonObjectMapper

/** 단위 테스트 — writer를 MockK로 대체, 파싱·검증·스킵 정책만 빠르게 검증. */
class EventsListenerTest :
    StringSpec({

        val good =
            """
            {"eventId": "e-1", "eventType": "click", "userId": "u-1", "itemId": "p-1",
             "ts": "2026-06-27T00:00:00Z", "context": {"requestId": "r-1"}}
            """.trimIndent()

        "정상 메시지는 타입드 Event로 파싱해 원본 그대로 저장한다" {
            val writer = mockk<BronzeWriter>()
            val eventSlot = slot<Event>()
            val rawSlot = slot<String>()
            every { writer.insert(capture(eventSlot), capture(rawSlot)) } returns true

            EventsListener(writer, jacksonObjectMapper()).onMessage(good)

            eventSlot.captured.eventType shouldBe EventType.CLICK
            eventSlot.captured.eventId shouldBe "e-1"
            eventSlot.captured.context?.requestId shouldBe "r-1"
            rawSlot.captured shouldBe good // 재직렬화 없이 원본 보존
        }

        "계약 위반은 저장 없이 스킵한다 (깨진 JSON · 모르는 타입 · 필수 필드 누락)" {
            val writer = mockk<BronzeWriter>()
            val listener = EventsListener(writer, jacksonObjectMapper())

            listener.onMessage("깨진 json {")
            listener.onMessage("""{"eventId": "e-2", "eventType": "wishlist", "ts": "2026-06-27T00:00:00Z"}""")
            listener.onMessage("""{"eventType": "click", "ts": "2026-06-27T00:00:00Z"}""") // eventId 누락

            verify(exactly = 0) { writer.insert(any(), any()) }
        }
    })
