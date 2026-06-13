package me.imweb.reco.serving.event

import io.kotest.core.annotation.Tags
import io.kotest.core.spec.style.StringSpec
import io.kotest.extensions.spring.SpringExtension
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.serialization.StringDeserializer
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.web.client.TestRestTemplate
import org.springframework.http.HttpStatus
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.containers.KafkaContainer
import org.testcontainers.utility.DockerImageName
import java.time.Duration
import java.util.Properties

/**
 * E2E (Testcontainers) — 실제 Kafka 를 띄우고 앱 전체를 기동해 `POST /events` 가 토픽에 produce 되는지 확인.
 * `@Tags("Integration")` 으로 기본 `test` 에서 제외, `./gradlew integrationTest` 에서만 실행(Docker 필요).
 */
@Tags("Integration")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class EventIngestE2ETest(
    private val restTemplate: TestRestTemplate,
) : StringSpec() {

    override fun extensions() = listOf(SpringExtension)

    init {
        "POST /events 는 Kafka events 토픽으로 produce 된다" {
            val body = listOf(
                mapOf("eventType" to "impression", "userId" to "u1", "itemId" to "i1"),
            )

            val response = restTemplate.postForEntity("/events", body, Map::class.java)
            response.statusCode shouldBe HttpStatus.ACCEPTED

            consumeOneValue("events").shouldNotBeNull()
        }
    }

    private fun consumeOneValue(topic: String): String? {
        val props = Properties().apply {
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
        private val kafka: KafkaContainer by lazy {
            KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.6.1")).also { it.start() }
        }

        @JvmStatic
        @DynamicPropertySource
        fun kafkaProps(registry: DynamicPropertyRegistry) {
            registry.add("spring.kafka.bootstrap-servers") { kafka.bootstrapServers }
        }
    }
}
