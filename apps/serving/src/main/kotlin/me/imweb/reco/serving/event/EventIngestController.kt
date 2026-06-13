package me.imweb.reco.serving.event

import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.beans.factory.annotation.Value
import org.springframework.http.HttpStatus
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import java.time.Instant
import java.util.UUID

/**
 * 이벤트 수집 API (#7).
 *
 * 동기 DB 쓰기 없이 Kafka로 produce하고 즉시 202를 반환한다(핫/콜드 패스 분리).
 * Bronze 적재는 Python 컨슈머(#13)가 비동기로 수행한다.
 */
@RestController
class EventIngestController(
    private val kafkaTemplate: KafkaTemplate<String, String>,
    private val objectMapper: ObjectMapper,
    @Value("\${app.kafka.events-topic}") private val topic: String,
) {

    data class IngestResponse(val accepted: Int)

    @PostMapping("/events")
    @ResponseStatus(HttpStatus.ACCEPTED)
    fun ingest(@RequestBody events: List<EventEnvelope>): IngestResponse {
        events.forEach { raw ->
            val enriched = raw.copy(
                eventId = raw.eventId ?: UUID.randomUUID().toString(),
                ts = raw.ts ?: Instant.now().toString(),
            )
            // fire-and-forget: send 결과를 블록하지 않는다.
            kafkaTemplate.send(topic, enriched.userId ?: enriched.eventId, objectMapper.writeValueAsString(enriched))
        }
        return IngestResponse(accepted = events.size)
    }
}
