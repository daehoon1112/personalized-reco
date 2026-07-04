package me.imweb.reco.bronzesink

import me.imweb.reco.event.Event
import org.slf4j.LoggerFactory
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component
import tools.jackson.core.JacksonException
import tools.jackson.databind.ObjectMapper

/**
 * `events` 토픽 리스너 — 파싱·검증(계약) 담당, 저장은 [BronzeWriter]에 위임.
 *
 * 계약 위반(깨진 JSON, 모르는 eventType, 필수 필드 누락)은 경고 남기고 스킵한다 —
 * 정상 리턴이므로 오프셋은 커밋되고(불량 메시지 무한 재소비 방지), DB 장애 등 인프라
 * 예외는 그대로 던져 컨테이너 기본 에러 핸들러(재시도)에 맡긴다.
 */
@Component
class EventsListener(
    private val writer: BronzeWriter,
    private val objectMapper: ObjectMapper,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @KafkaListener(topics = ["\${app.kafka.events-topic}"])
    fun onMessage(raw: String) {
        val event = try {
            objectMapper.readValue(raw, Event::class.java)
        } catch (e: JacksonException) {
            log.warn("skip bad message: {}", e.message)
            return
        } catch (e: IllegalArgumentException) {
            log.warn("skip bad message: {}", e.message)
            return
        }
        val inserted = writer.insert(event, raw)
        if (!inserted) log.debug("duplicate event skipped: {}", event.eventId)
    }
}
