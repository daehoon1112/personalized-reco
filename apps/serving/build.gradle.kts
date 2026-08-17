plugins {
    kotlin("jvm")
    kotlin("plugin.spring")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
    id("org.flywaydb.flyway")
}

group = "me.imweb.reco"
version = "0.0.1-SNAPSHOT"

// Boot BOM이 관리하는 kotlin-stdlib(2.2.x)을 플러그인과 같은 2.3.21로 정렬
extra["kotlin.version"] = "2.3.21"

repositories {
    mavenCentral()
}

// JDK 25 (로컬 설치 JDK와 일치 — Gradle 9.6+/Boot 4.0+/Kotlin 2.2.20+ 지원 범위)
kotlin {
    jvmToolchain(25)
}

dependencies {
    implementation(project(":packages:event-contract")) // Event/EventType/EventContext 공유 계약
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-kafka") // Boot 4: Kafka 자동설정 모듈 분리 (spring-kafka 포함)
    implementation("tools.jackson.module:jackson-module-kotlin") // Boot 4 = Jackson 3 (tools.jackson)
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    // DB 스키마 소유권(#5): Flyway 마이그레이션 + Postgres (버전은 Spring Boot BOM이 관리)
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.springframework.boot:spring-boot-flyway") // Boot 4: Flyway 자동설정 모듈 분리
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    runtimeOnly("org.postgresql:postgresql")

    // bootRun 시 infra/docker-compose.yml 자동 기동 (jar에는 미포함)
    developmentOnly("org.springframework.boot:spring-boot-docker-compose")

    // 테스트: Kotest(러너+단언) + MockK + Testcontainers (TC 버전은 Boot BOM의 testcontainers-bom이 관리)
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test") // MockMvc + TestRestTemplate(resttestclient)
    testImplementation("org.springframework.boot:spring-boot-starter-restclient") // TestRestTemplate 자동설정이 RestTemplateBuilder 요구
    testImplementation("io.kotest:kotest-runner-junit5:6.2.1")
    testImplementation("io.kotest:kotest-assertions-core:6.2.1")
    testImplementation("io.kotest:kotest-extensions-spring:6.2.1")
    // AGENTS 규칙 중 구조로 판정 가능한 것(레이어·경계)을 문장이 아니라 테스트로 강제한다(ArchitectureSpec).
    // ktlint 는 포맷만 본다.
    testImplementation("com.lemonappdev:konsist:0.17.3")
    testImplementation("io.mockk:mockk:1.14.11")
    testImplementation("org.testcontainers:testcontainers-kafka")
    testImplementation("org.testcontainers:testcontainers-postgresql")
}

// 로컬 bootRun = 개발 실행: 인프라 자동 기동(docker-compose 모듈) + 샘플 데이터 시드(seed 프로파일).
// 운영 배포(jar 실행)에는 developmentOnly 의존성도, 이 프로파일도 적용되지 않는다.
tasks.named<org.springframework.boot.gradle.tasks.run.BootRun>("bootRun") {
    args("--spring.profiles.active=seed")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}

// 기본 test = 단위만 (Docker 불필요). Integration 태그 제외.
tasks.named<Test>("test") {
    systemProperty("kotest.tags", "!Integration")
}

// integrationTest = Testcontainers E2E (Docker 필요). Integration 태그만.
tasks.register<Test>("integrationTest") {
    description = "Testcontainers 통합/E2E 테스트 (Docker 필요)"
    group = "verification"
    testClassesDirs =
        sourceSets.test
            .get()
            .output.classesDirs
    classpath = sourceSets.test.get().runtimeClasspath
    systemProperty("kotest.tags", "Integration")
    shouldRunAfter("test")
}

// 앱 기동 없이 스키마만 반영: ./gradlew :apps:serving:flywayMigrate (Python 컨슈머만 쓰는 워크플로 대비)
flyway {
    url = System.getenv("DB_URL") ?: "jdbc:postgresql://localhost:5432/reco"
    user = System.getenv("DB_USER") ?: "reco"
    password = System.getenv("DB_PASSWORD") ?: "reco"
    locations = arrayOf("filesystem:src/main/resources/db/migration")
}
