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

kotlin {
    jvmToolchain(25)
}

dependencies {
    implementation(project(":packages:event-contract")) // Event 계약 (serving과 공유)
    implementation("org.springframework.boot:spring-boot-starter") // 웹 없음 — 헤드리스 데몬
    implementation("org.springframework.boot:spring-boot-starter-kafka")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.springframework.boot:spring-boot-starter-jackson")
    implementation("tools.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    runtimeOnly("org.postgresql:postgresql")
    // 스키마(Flyway)는 serving이 소유한다 — 이 앱은 events_raw가 있다고 가정하고 쓰기만 한다

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("io.kotest:kotest-runner-junit5:6.2.1")
    testImplementation("io.kotest:kotest-assertions-core:6.2.1")
    testImplementation("io.kotest:kotest-extensions-spring:6.2.1")
    testImplementation("io.mockk:mockk:1.14.11")
    testImplementation("org.testcontainers:testcontainers-kafka")
    testImplementation("org.testcontainers:testcontainers-postgresql")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}

tasks.named<Test>("test") {
    systemProperty("kotest.tags", "!Integration")
}

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
