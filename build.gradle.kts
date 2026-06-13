// 폴리글랏 모노레포의 JVM(Kotlin/Gradle) 측 루트.
// 플러그인 버전은 여기서 한 번만 선언하고(apply false), 각 모듈이 버전 없이 적용한다.
// Python(uv) 측은 pyproject.toml 워크스페이스로 관리되며, 루트 Makefile이 둘을 묶는다.
plugins {
    kotlin("jvm") version "2.1.0" apply false
    kotlin("plugin.spring") version "2.1.0" apply false
    id("org.springframework.boot") version "3.4.1" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
}
