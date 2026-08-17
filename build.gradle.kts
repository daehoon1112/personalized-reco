// 폴리글랏 모노레포의 JVM(Kotlin/Gradle) 측 루트.
// 플러그인 버전은 여기서 한 번만 선언하고(apply false), 각 모듈이 버전 없이 적용한다.
// Python(uv) 측은 pyproject.toml 워크스페이스로 관리되며, 루트 Makefile이 둘을 묶는다.
//
// 버전 체인 (JDK 25 기준): Gradle 9.6+ (Java 25 데몬 지원) · Kotlin 2.3.21(JVM target 25 지원, Boot BOM stdlib은 ext로 정렬)
// · Spring Boot 4.0.x · Flyway 11.14.x(Boot BOM과 일치)

// Flyway 10부터 DB별 지원이 분리돼, Gradle 플러그인(flywayMigrate)이 Postgres를 다루려면
// 플러그인 클래스패스(buildscript)에 DB 모듈과 드라이버가 있어야 한다.
buildscript {
    dependencies {
        classpath("org.flywaydb:flyway-database-postgresql:11.14.1")
        classpath("org.postgresql:postgresql:42.7.12")
    }
}

plugins {
    kotlin("jvm") version "2.3.21" apply false
    kotlin("plugin.spring") version "2.3.21" apply false
    id("org.springframework.boot") version "4.0.7" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
    id("org.flywaydb.flyway") version "11.14.1" apply false
    id("org.jlleitschuh.gradle.ktlint") version "13.1.0" apply false
}

// ktlint(포맷)만 여기서 일괄 적용한다 — 모듈마다 같은 설정을 복사하면 규칙이 갈라지기 때문이다.
// 포맷과 구조는 역할을 나눈다: 여기(ktlint)는 스타일만 보고, 레이어·경계 규칙은 문서가 아니라
// 테스트(구조 검증)로 강제한다. 파일 단위 예외는 .editorconfig 에 사유와 함께 남긴다.
// 컨테이너 프로젝트(:apps, :packages)는 Kotlin 소스도 repositories 선언도 없다 —
// 거기까지 적용하면 ktlint 의존성을 못 받아 빌드가 깨지므로, kotlin("jvm")을 쓴 모듈에만 붙인다.
subprojects {
    plugins.withId("org.jetbrains.kotlin.jvm") {
        apply(plugin = "org.jlleitschuh.gradle.ktlint")

        configure<org.jlleitschuh.gradle.ktlint.KtlintExtension> {
            version.set("1.5.0")
            android.set(false)
            outputToConsole.set(true)
            reporters {
                reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.PLAIN)
                reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.CHECKSTYLE)
            }
        }
    }
}
