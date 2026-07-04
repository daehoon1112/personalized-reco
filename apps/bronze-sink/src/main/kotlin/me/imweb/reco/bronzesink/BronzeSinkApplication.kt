package me.imweb.reco.bronzesink

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

/**
 * Kafka `events` → bronze(events_raw) 적재 데몬 (#13, Python 컨슈머를 대체).
 *
 * 상시 실행 컨슈머라 배치(apps/pipelines)와 분리된 독립 앱이다.
 * 처리 흐름: [EventsListener](파싱·검증) → [BronzeWriter](멱등 INSERT).
 * at-least-once(ack-mode: record) + ON CONFLICT(event_id) DO NOTHING = 사실상 정확히 한 번.
 */
@SpringBootApplication
class BronzeSinkApplication

fun main(args: Array<String>) {
    runApplication<BronzeSinkApplication>(*args)
}
