package me.imweb.reco.serving

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.verify.assertTrue
import io.kotest.core.spec.style.StringSpec

// Konsist 의 기본 스코프(scopeFromProject)는 git 루트부터 훑어 다른 모듈까지 끌고 온다.
// 규칙의 주인이 모듈이므로 스코프도 모듈로 못 박는다(경로는 저장소 루트 기준).
private const val SERVING_MAIN = "apps/serving/src/main"
private const val SERVING_TEST = "apps/serving/src/test"

/**
 * 레이어·경계 규칙을 문장이 아니라 소스 구조로 강제한다.
 *
 * 문서에 적힌 규칙은 시간이 지나면 코드와 갈라진다(실제로 이 저장소에서도 문서가 먼저 틀렸다).
 * 구문으로 판정 가능한 것은 여기로 내리고, 규칙을 완화해야 한다면 문서가 아니라 이 파일을 고친다.
 * ktlint 는 포맷만 본다 — 구조는 여기가 본다.
 */
class ArchitectureSpec :
    StringSpec({

        /**
         * 서빙의 DB 접근은 어댑터(catalog/, 이후 persistence/)에만 둔다.
         *
         * 컨트롤러가 JdbcClient 를 직접 잡기 시작하면 "서빙은 사전계산 결과를 읽기만 한다"는 경계가
         * 조용히 무너지고, 쿼리가 컨트롤러마다 흩어져 핫 패스 비용을 추적할 수 없게 된다.
         */
        "JDBC 접근은 어댑터(catalog·persistence)에서만 한다" {
            val adapterPaths = listOf("/catalog/", "/persistence/")
            Konsist
                .scopeFromDirectory(SERVING_MAIN)
                .files
                .filterNot { file -> adapterPaths.any { file.path.contains(it) } }
                .assertTrue(additionalMessage = "쿼리는 어댑터(예: CatalogReader)로 내린다. 컨트롤러·도메인은 DB 를 모른다") { file ->
                    file.imports.none { it.name.startsWith("org.springframework.jdbc") }
                }
        }

        /**
         * 도메인 타입은 프레임워크에 의존하지 않는다.
         *
         * `impression_label` 같은 테이블 대응 타입에 JPA·Jackson 어노테이션이 붙기 시작하면,
         * 도메인 규칙(퍼널 정합성 등)이 직렬화·매핑 사정에 끌려다닌다. 매핑은 어댑터의 몫이다.
         */
        "domain 은 Spring·JPA·Jackson 을 import 하지 않는다" {
            Konsist
                .scopeFromDirectory(SERVING_MAIN)
                .files
                .filter { it.path.contains("/domain/") }
                .assertTrue(additionalMessage = "도메인은 순수 Kotlin 으로 둔다. 매핑·직렬화는 어댑터에서 처리한다") { file ->
                    file.imports.none {
                        it.name.startsWith("org.springframework") ||
                            it.name.startsWith("jakarta.persistence") ||
                            it.name.startsWith("tools.jackson") ||
                            it.name.startsWith("com.fasterxml.jackson")
                    }
                }
        }

        /**
         * Kafka produce 는 수집 경로(event/)에서만 한다.
         *
         * 추천 응답 경로에서 직접 produce 하기 시작하면 "핫 패스는 produce 후 즉시 반환"이라는
         * 분리가 깨지고, 노출 로깅이 응답 지연에 얹힌다. 서빙 API 의 impression 로깅도
         * 같은 수집 경로를 통하게 한다.
         */
        "KafkaTemplate 은 수집 경로(event)에서만 잡는다" {
            Konsist
                .scopeFromDirectory(SERVING_MAIN)
                .files
                .filterNot { it.path.contains("/event/") }
                .assertTrue(additionalMessage = "produce 는 수집 경로(event/)를 통한다 — 핫 패스 분리를 코드로 유지한다") { file ->
                    file.imports.none { it.name.startsWith("org.springframework.kafka") }
                }
        }

        /**
         * Testcontainers 를 쓰는 스펙은 반드시 Integration 태그를 단다.
         *
         * 태그를 빼먹으면 그 스펙이 기본 `gradle test` 로 흘러들어가고, Docker 없는 환경(=CI 기본,
         * 새로 받은 로컬)에서 "빠른 테스트"가 갑자기 Docker 를 요구하며 깨진다.
         * 태그 분리는 docs/testing.md 의 약속이라 문서가 아니라 여기서 지킨다.
         */
        "Testcontainers 스펙은 Integration 태그를 단다" {
            Konsist
                .scopeFromDirectory(SERVING_TEST)
                .files
                .filter { file -> file.imports.any { it.name.startsWith("org.testcontainers") } }
                .assertTrue(additionalMessage = "Docker 가 필요한 스펙은 @Tags(\"Integration\") 을 달아 integrationTest 로 분리한다") { file ->
                    file.imports.any { it.name == "io.kotest.core.annotation.Tags" }
                }
        }
    })
