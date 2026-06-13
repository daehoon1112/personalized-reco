plugins {
    kotlin("jvm")
    kotlin("plugin.spring")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
}

group = "me.imweb.reco"
version = "0.0.1-SNAPSHOT"

repositories {
    mavenCentral()
}

// JDK 21 LTS 고정 (로컬은 JDK 25도 있으나 호환성 위해 21로 컴파일/실행).
kotlin {
    jvmToolchain(21)
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    // 테스트: Kotest(러너+단언) + MockK + Testcontainers
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("io.kotest:kotest-runner-junit5:5.9.1")
    testImplementation("io.kotest:kotest-assertions-core:5.9.1")
    testImplementation("io.kotest.extensions:kotest-extensions-spring:1.3.0")
    testImplementation("io.mockk:mockk:1.13.13")
    testImplementation("org.testcontainers:kafka") // 버전은 Spring Boot BOM이 관리
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
    testClassesDirs = sourceSets.test.get().output.classesDirs
    classpath = sourceSets.test.get().runtimeClasspath
    systemProperty("kotest.tags", "Integration")
    shouldRunAfter("test")
}
