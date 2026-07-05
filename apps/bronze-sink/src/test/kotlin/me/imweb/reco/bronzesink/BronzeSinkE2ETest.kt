package me.imweb.reco.bronzesink

import io.kotest.core.annotation.Tags
import io.kotest.core.spec.style.StringSpec
import io.kotest.extensions.spring.SpringExtension
import io.kotest.matchers.shouldBe
import java.time.Duration
import java.util.Properties
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerRecord
import org.apache.kafka.common.serialization.StringSerializer
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.kafka.KafkaContainer
import org.testcontainers.postgresql.PostgreSQLContainer
import org.testcontainers.utility.DockerImageName

/**
 * E2E (Testcontainers) — 실제 Kafka+Postgres에서 produce → 리스너 → bronze 적재 + 멱등성 확인.
 * 스키마는 serving(Flyway) 소유라 여기선 events_raw DDL만 직접 만든다.
 */
@Tags("Integration")
@SpringBootTest
class BronzeSinkE2ETest : StringSpec() {

    @Autowired
    private lateinit var jdbc: JdbcClient

    init {
        extensions(SpringExtension())

        "produce된 이벤트가 bronze에 멱등 적재된다" {
            jdbc.sql(BRONZE_DDL).update()

            val evt = """
                {"eventId": "evt-e2e-1", "eventType": "click", "userId": "u1", "itemId": "i1",
                 "ts": "2026-07-04T00:00:00Z", "context": {"requestId": "r-1"}}
            """.trimIndent()
            produce(evt)
            produce(evt) // 같은 event_id 두 번 → 한 행이어야 함
            produce("""{"eventId": "evt-e2e-bad", "eventType": "wishlist", "ts": "2026-07-04T00:00:00Z"}""")

            val count = awaitRowCount("evt-e2e-1", atLeast = 1)
            count shouldBe 1

            // 불량 메시지는 적재되지 않아야 한다
            countOf("evt-e2e-bad") shouldBe 0
        }
    }

    private fun produce(json: String) {
        val props = Properties().apply {
            put("bootstrap.servers", kafka.bootstrapServers)
            put("key.serializer", StringSerializer::class.java.name)
            put("value.serializer", StringSerializer::class.java.name)
        }
        KafkaProducer<String, String>(props).use { p ->
            p.send(ProducerRecord("events", json)).get()
        }
    }

    private fun countOf(eventId: String): Long =
        jdbc.sql("SELECT count(*) FROM events_raw WHERE event_id = :id")
            .param("id", eventId).query(Long::class.java).single()

    private fun awaitRowCount(eventId: String, atLeast: Long): Long {
        val deadline = System.currentTimeMillis() + Duration.ofSeconds(20).toMillis()
        while (System.currentTimeMillis() < deadline) {
            val n = countOf(eventId)
            if (n >= atLeast) {
                Thread.sleep(1500) // 중복 produce 처리까지 잠깐 더 기다린 뒤 최종 개수 반환
                return countOf(eventId)
            }
            Thread.sleep(300)
        }
        return countOf(eventId)
    }

    companion object {
        private val kafka: KafkaContainer by lazy {
            KafkaContainer(DockerImageName.parse("apache/kafka:4.0.0")).also { it.start() }
        }
        private val postgres: PostgreSQLContainer by lazy {
            PostgreSQLContainer(DockerImageName.parse("postgres:16")).also { it.start() }
        }

        private val BRONZE_DDL = """
            CREATE TABLE IF NOT EXISTS events_raw (
                id          BIGSERIAL   PRIMARY KEY,
                event_id    TEXT        NOT NULL UNIQUE,
                event_type  TEXT        NOT NULL,
                user_id     TEXT,
                item_id     TEXT,
                session_id  TEXT,
                position    INTEGER,
                consent     BOOLEAN,
                event_ts    TIMESTAMPTZ NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                payload     JSONB       NOT NULL
            )
        """.trimIndent()

        @JvmStatic
        @DynamicPropertySource
        fun containerProps(registry: DynamicPropertyRegistry) {
            registry.add("spring.kafka.bootstrap-servers") { kafka.bootstrapServers }
            registry.add("spring.datasource.url") { postgres.jdbcUrl }
            registry.add("spring.datasource.username") { postgres.username }
            registry.add("spring.datasource.password") { postgres.password }
        }
    }
}
