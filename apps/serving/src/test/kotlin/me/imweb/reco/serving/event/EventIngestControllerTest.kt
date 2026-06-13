package me.imweb.reco.serving.event

import com.fasterxml.jackson.databind.ObjectMapper
import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe
import io.kotest.matchers.string.shouldContain
import io.mockk.every
import io.mockk.mockk
import io.mockk.slot
import io.mockk.verify
import org.springframework.kafka.core.KafkaTemplate

/** 단위 테스트 — KafkaTemplate 을 MockK 로 모킹해 produce 로직만 빠르게 검증. */
class EventIngestControllerTest : StringSpec({

    "이벤트당 정확히 한 번 produce 하고 accepted 개수를 반환한다" {
        val kafka = mockk<KafkaTemplate<String, String>>(relaxed = true)
        val controller = EventIngestController(kafka, ObjectMapper(), "events")

        val events = listOf(
            EventEnvelope(eventType = "impression", userId = "u1", itemId = "i1"),
            EventEnvelope(eventType = "click", userId = "u1", itemId = "i1"),
        )

        controller.ingest(events).accepted shouldBe 2
        verify(exactly = 2) { kafka.send(eq("events"), any(), any()) }
    }

    "eventId/ts 가 없으면 produce 전에 채워 넣는다" {
        val kafka = mockk<KafkaTemplate<String, String>>(relaxed = true)
        val controller = EventIngestController(kafka, ObjectMapper(), "events")
        val payload = slot<String>()
        every { kafka.send(eq("events"), any(), capture(payload)) } returns mockk(relaxed = true)

        controller.ingest(listOf(EventEnvelope(eventType = "purchase", userId = "u9")))

        payload.captured shouldContain "\"eventId\""
        payload.captured shouldContain "\"ts\""
    }
})
