package me.imweb.reco.bronzesink

import me.imweb.reco.event.Event
import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.stereotype.Repository

/**
 * bronze(events_raw) 멱등 쓰기. payload는 재직렬화 없이 **원본 그대로** 보존한다(받은 그대로 원칙).
 */
@Repository
class BronzeWriter(
    private val jdbc: JdbcClient,
) {
    /** @return 실제로 삽입됐으면 true, 중복(event_id 충돌)이면 false */
    fun insert(
        event: Event,
        rawPayload: String,
    ): Boolean {
        val updated =
            jdbc
                .sql(INSERT_SQL)
                .param("event_id", event.eventId)
                .param("event_type", event.eventType.code)
                .param("user_id", event.userId)
                .param("item_id", event.itemId)
                .param("session_id", event.sessionId)
                .param("position", event.position)
                .param("consent", event.consent)
                .param("event_ts", java.sql.Timestamp.from(event.ts))
                .param("payload", rawPayload)
                .update()
        return updated == 1
    }

    companion object {
        private val INSERT_SQL =
            """
            INSERT INTO events_raw
                (event_id, event_type, user_id, item_id, session_id, position, consent, event_ts, payload)
            VALUES
                (:event_id, :event_type, :user_id, :item_id, :session_id,
                 :position, :consent, :event_ts, :payload::jsonb)
            ON CONFLICT (event_id) DO NOTHING
            """.trimIndent()
    }
}
