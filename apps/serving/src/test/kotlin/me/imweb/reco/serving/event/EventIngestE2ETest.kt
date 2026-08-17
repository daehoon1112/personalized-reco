package me.imweb.reco.serving.event

import io.kotest.core.annotation.Tags
import io.kotest.core.spec.style.StringSpec
import io.kotest.extensions.spring.SpringExtension
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.serialization.StringDeserializer
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.resttestclient.TestRestTemplate
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureTestRestTemplate
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.http.HttpStatus
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.kafka.KafkaContainer
import org.testcontainers.postgresql.PostgreSQLContainer
import org.testcontainers.utility.DockerImageName
import java.time.Duration
import java.util.Properties

/**
 * E2E (Testcontainers) — 실제 Kafka 를 띄우고 앱 전체를 기동해 `POST /events` 가 토픽에 produce 되는지 확인.
 * `@Tags("Integration")` 으로 기본 `test` 에서 제외, `./gradlew integrationTest` 에서만 실행(Docker 필요).
 */
@Tags("Integration")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureTestRestTemplate // Boot 4: RANDOM_PORT만으로는 TestRestTemplate 빈이 안 뜬다
class EventIngestE2ETest : StringSpec() {
    // Kotest 6는 생성자 주입에 프로젝트 레벨 확장 등록이 필요 → 필드 주입으로 대체.
    @Autowired
    private lateinit var restTemplate: TestRestTemplate

    init {
        extensions(SpringExtension())

        "POST /events 는 Kafka events 토픽으로 produce 된다" {
            val body =
                listOf(
                    mapOf("eventType" to "impression", "userId" to "u1", "itemId" to "i1"),
                )

            val response = restTemplate.postForEntity("/events", body, Map::class.java)
            response.statusCode shouldBe HttpStatus.ACCEPTED

            consumeOneValue("events").shouldNotBeNull()
        }
    }

    private fun consumeOneValue(topic: String): String? {
        val props =
            Properties().apply {
                put("bootstrap.servers", kafka.bootstrapServers)
                put("group.id", "e2e-verify")
                put("auto.offset.reset", "earliest")
                put("key.deserializer", StringDeserializer::class.java.name)
                put("value.deserializer", StringDeserializer::class.java.name)
            }
        KafkaConsumer<String, String>(props).use { consumer ->
            consumer.subscribe(listOf(topic))
            val deadline = System.currentTimeMillis() + 10_000
            while (System.currentTimeMillis() < deadline) {
                val records = consumer.poll(Duration.ofMillis(500))
                if (!records.isEmpty) return records.iterator().next().value()
            }
        }
        return null
    }

    companion object {
        // lazy: 컨테이너는 첫 접근(통합 테스트 컨텍스트 기동) 시에만 시작 → 단위 test 에서는 절대 안 뜬다.
        // Testcontainers 2.x 신형 KafkaContainer(apache/kafka 이미지, KRaft). 3.9.0은 TC2 기동 스크립트와
        // 비호환(exit 1)이라 4.x 사용.
        private val kafka: KafkaContainer by lazy {
            KafkaContainer(DockerImageName.parse("apache/kafka:4.0.0")).also { it.start() }
        }

        // 앱 기동 시 Flyway가 실제 마이그레이션(V1~V4)을 실행 → 스키마 유효성도 함께 검증된다.
        private val postgres: PostgreSQLContainer by lazy {
            PostgreSQLContainer(DockerImageName.parse("postgres:16")).also { it.start() }
        }

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
