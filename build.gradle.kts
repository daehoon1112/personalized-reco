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
}
