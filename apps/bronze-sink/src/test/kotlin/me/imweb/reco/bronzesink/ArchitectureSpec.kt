package me.imweb.reco.bronzesink

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.verify.assertTrue
import io.kotest.core.spec.style.StringSpec

// Konsist 의 기본 스코프(scopeFromProject)는 git 루트부터 훑어 다른 모듈까지 끌고 온다.
// 규칙의 주인이 모듈이므로 스코프도 모듈로 못 박는다(경로는 저장소 루트 기준).
private const val SINK_MAIN = "apps/bronze-sink/src/main"
private const val SINK_TEST = "apps/bronze-sink/src/test"

/**
 * 컨슈머의 역할 분리를 소스 구조로 강제한다 — 문장이 아니라 테스트가 지킨다.
 *
 * 이 앱은 "받은 그대로 적재"가 전부라 규칙이 단순한 대신 어기기도 쉽다:
 * 리스너가 직접 SQL 을 쓰기 시작하면 파싱·검증(계약)과 적재(멱등)가 한 덩어리가 되고,
 * 그때부터 "불량 메시지는 스킵, 인프라 예외는 재시도"라는 오프셋 정책을 테스트로 고정할 수 없다.
 */
class ArchitectureSpec :
    StringSpec({

        "JDBC 접근은 적재 어댑터(*Writer)에서만 한다" {
            Konsist
                .scopeFromDirectory(SINK_MAIN)
                .files
                .filterNot { it.name.endsWith("Writer") }
                .assertTrue(additionalMessage = "적재는 BronzeWriter 로 내린다. 리스너는 파싱·검증(계약)만 맡는다") { file ->
                    file.imports.none { it.name.startsWith("org.springframework.jdbc") }
                }
        }

        "Kafka 소비 진입점은 리스너 한 곳뿐이다" {
            Konsist
                .scopeFromDirectory(SINK_MAIN)
                .files
                .filterNot { it.name.endsWith("Listener") }
                .assertTrue(additionalMessage = "@KafkaListener 는 EventsListener 한 곳에만 둔다 — 오프셋 정책이 갈라지지 않게") { file ->
                    file.imports.none { it.name.startsWith("org.springframework.kafka.annotation") }
                }
        }

        /**
         * Testcontainers 를 쓰는 스펙은 반드시 Integration 태그를 단다.
         *
         * 태그를 빼먹으면 그 스펙이 기본 `gradle test` 로 흘러들어가 Docker 없는 환경에서 깨진다.
         */
        "Testcontainers 스펙은 Integration 태그를 단다" {
            Konsist
                .scopeFromDirectory(SINK_TEST)
                .files
                .filter { file -> file.imports.any { it.name.startsWith("org.testcontainers") } }
                .assertTrue(additionalMessage = "Docker 가 필요한 스펙은 @Tags(\"Integration\") 을 달아 integrationTest 로 분리한다") { file ->
                    file.imports.any { it.name == "io.kotest.core.annotation.Tags" }
                }
        }
    })
