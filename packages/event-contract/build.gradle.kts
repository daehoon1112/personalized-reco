// 이벤트 계약 공유 모듈 — serving(수집)과 bronze-sink(적재)가 함께 쓴다.
// 순수 Kotlin 라이브러리로 유지한다(Spring/Boot 플러그인 없음). 의존성은 잭슨 어노테이션 하나뿐이라
// BOM 대신 명시 버전으로 고정 — Boot BOM(2.21 관리)과 어긋나면 컴파일에서 드러난다.
plugins {
    kotlin("jvm")
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
    api("com.fasterxml.jackson.core:jackson-annotations:2.21") // @JsonValue (Jackson 3에서도 이 패키지 유지)
}
